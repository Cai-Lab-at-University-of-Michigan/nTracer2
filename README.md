# nTracer2

## Startup
To start nTracer2 with defaults and connect to Cai Lab's demo dataset, run:
```
docker compose build
docker compose up
```

## Change CDN URL and dataset
To change the URL for the image source and the dataset ID, we specify the build args:
```
docker build --build-arg cdn_url=https://sonic2.cai-lab.org/data/ --build-arg dataset_id=packed2 -t ntracer2 .
```

Additional args to customize exposed port and public address (if hosting on a server):
```
docker build --build-arg server_port=8080 --build-arg neuroglancer_port=8050  --build-arg public_url=https://ntracer.cai-lab.org -t ntracer2 .
```
