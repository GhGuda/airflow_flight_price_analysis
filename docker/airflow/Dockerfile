FROM apache/airflow:2.8.1-python3.10

# Switch to root to install dependencies
USER root

# System dependencies (for mysql, postgres drivers)
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    libpq-dev \
    && apt-get clean

# Switch back to airflow user
USER airflow

# Copy Python dependencies
COPY requirements/prod.txt /requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /requirements.txt

# Copy DAGs and source code
COPY dags /opt/airflow/dags
COPY src /opt/airflow/src

# Ensure src is on PYTHONPATH
ENV PYTHONPATH=/opt/airflow
