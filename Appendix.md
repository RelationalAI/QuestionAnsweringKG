### APPENDIX

If you would like help with Docker, Snowflake

#### A : Extra Commands for Docker -

--  To see all images
```sh
docker images
```

-- To drop an image using image_id ( the *docker images* command will give the image ID )
```sh
docker rmi -f <image_id>
```

-- To drop an image using repository name ( the *docker images* command will give the Repository Name )
```sh
docker rmi <repo_name>
```

-- Login to the container and run through container terminal

```sh
docker run --platform linux/amd64 -p 8000:8000 <account_name>.registry.snowflakecomputing.com/<db_name>/<schema_name>/<image_repo_name>/<image_name>
```

-- Login to the container and Run from inside the container
```sh
docker run -it <account_name>.registry.snowflakecomputing.com/<db_name>/<schema_name>/<image_repo_name>/<image_name> /bin/bash
```

#### B : SQL Commands to delete Snowflake Objects

```sh
-- delete a compute pool from Snowflake
drop compute pool <cp_name>;

-- delete warehouse
drop warehouse <wh_name>;

-- delete database
drop database <db_name>;

--delete service
drop service <service_name>

-- list all compute pools
drop compute pool <cp_name>
```

------------------------------------------------------------------

#### C : Additional Resources

Install Docker - https://docs.docker.com/desktop/install/mac-install/

Snowflake Services - https://docs.snowflake.com/en/developer-guide/snowpark-container-services/overview-tutorials

------------------------------------------------------------------
