from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "/opt/airflow/project"

with DAG(
    dag_id="daily_pipeline",
    start_date=datetime(2024, 9, 1),
    schedule_interval="0 6 * * *",
    catchup=False,
) as dag:

    generate = BashOperator(
        task_id="generate_data",
        bash_command=f"python {PROJECT}/scripts/generate_synthetic_data.py",
    )

    load = BashOperator(
        task_id="load_bronze",
        bash_command=f"python {PROJECT}/scripts/load_bronze.py",
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {PROJECT}/supplypulse_dbt && "
            f"dbt build --profiles-dir /opt/airflow/dbt_profiles"
        ),
    )

    notify = BashOperator(
        task_id="notify",
        bash_command='echo "Pipeline completed at $(date)"',
    )

    generate >> load >> dbt_build >> notify
