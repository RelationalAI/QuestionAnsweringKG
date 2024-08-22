# Use a base image with Miniconda installed
FROM continuumio/miniconda3

# Set a working directory
WORKDIR /app


# Create a Conda environment and activate it
RUN conda create --name kgqa_env python=3.10 --yes
RUN echo "source activate kgqa_env" > ~/.bashrc
ENV PATH /opt/conda/envs/kgqa_env/bin:$PATH

# Install other dependencies from requirements.txt
COPY ./kgqa/kgqa/ /app/kgqa/kgqa
COPY ./kgqa/requirements.txt /app/kgqa/requirements.txt
COPY ./kgqa/data/ /app/kgqa/data
COPY ./kgqa_api_service/ /app/kgqa_api_service
COPY ./QueryCortexAI/ /app/QueryCortexAI
COPY Dockerfile /app/Dockerfile

ENV PYTHONPATH="/app/"

RUN ls -la /app/kgqa
RUN cat /app/kgqa/requirements.txt

RUN pip install --no-cache-dir -r /app/kgqa/requirements.txt
RUN conda install -c pytorch faiss-cpu --yes
RUN pip freeze && sleep 30

# Expose the port the app runs on
EXPOSE 8000
EXPOSE 8001

# Define the command to run your application
CMD ["python", "./kgqa_api_service/kgqa_service.py"]
