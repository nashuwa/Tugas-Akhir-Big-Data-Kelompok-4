import docker
import os
from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount
from datetime import datetime

# Configuration (gunakan MongoDB Atlas yang sudah ada)
used_path = '/app/output/tickers_data.json'
mongo_db = 'bigdata_saham'  # Database yang sudah ada di Atlas

# Mendapatkan path host yang benar dari mount container saat ini
try:
    client = docker.from_env()
    current_container = client.containers.get(os.environ['HOSTNAME'])
    for mount in current_container.attrs['Mounts']:
        if mount['Destination'] == '/opt/airflow/output':
            host_output_path = mount['Source'] 
            break
    else:
        raise Exception("Mount point /opt/airflow/output not found in container")
    
    print("Host output path:", host_output_path)
except Exception as e:
    print(f"Warning: Could not get host path: {e}")
    host_output_path = "/tmp/output"  # Fallback

default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 5, 10),
    'retries': 1
}

with DAG(
    dag_id='yfinance_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    tags=['saham', 'atlas'],
) as dag:
    
    # TASK: EXTRACT (5 years data)
    extract_yfinance = DockerOperator(
        task_id='extract_yfinance',
        image='yfinance_extraction:latest',
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="saham_net",
        mount_tmp_dir=False,
        mounts=[
            Mount(source=host_output_path, target='/app/output', type='bind')
        ],
        command="python yfinance_data_fetcher_5years.py",
        container_name="pipeline_extract_yfinance",  # Fixed: unique name
        environment={
            'EXCEL_FILE_PATH': '/app/tickers.xlsx',
            'YFINANCE_OUTPUT_PATH': used_path,
            'PYTHONUNBUFFERED': '1'
        },
    )
    
    # TASK: LOAD (ke MongoDB Atlas)
    load_yfinance = DockerOperator(
        task_id='load_yfinance',
        image='yfinance-load:latest',
        auto_remove=True,
        docker_url="unix://var/run/docker.sock",
        network_mode="saham_net",
        mount_tmp_dir=False,
        mounts=[
            Mount(source=host_output_path, target='/app/output', type='bind')
        ],
        command="python yfinance-load.py",
        container_name="pipeline_load_yfinance",  # Fixed: unique name
        environment={
            # GUNAKAN MONGODB ATLAS
            'MONGO_URI': 'mongodb+srv://coffeelatte:secretdata3@luna.sryzase.mongodb.net/',
            'MONGO_DB': mongo_db,  # bigdata_saham
            'INPUT_PATH': used_path,
            'PYTHONUNBUFFERED': '1'
        },
    )
    
    # DEPENDENCY
    extract_yfinance >> load_yfinance