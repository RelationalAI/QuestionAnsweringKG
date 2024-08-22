# Use a base image with Miniconda installed
FROM continuumio/miniconda3

# Set a working directory
WORKDIR /app


# Create a Conda environment and activate it
RUN conda create --name kgqa_env python=3.10 --yes
RUN echo "source activate kgqa_env" > ~/.bashrc
ENV PATH /opt/conda/envs/kgqa_env/bin:$PATH

# Install other dependencies from requirements.txt
COPY ./ /app/

ENV PYTHONPATH="/app/"

RUN cat /app/requirements.txt

RUN pip install --no-cache-dir -r /app/requirements.txt
RUN conda install -c pytorch faiss-cpu --yes

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run your application
CMD ["python", "./setup.py","ComputeEmbeddings"]
