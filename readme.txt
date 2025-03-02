build and push the docker container
-----------------------------------

docker build -t us-central1-docker.pkg.dev/sofe4630/dataflow-docker/pedestrian_occlusion:latest .
docker push us-central1-docker.pkg.dev/sofe4630/dataflow-docker/pedestrian_occlusion:latest

stage the template file (put your bucket and project name)
----------------------------------------------------------

gcloud dataflow flex-template build gs://sofe4630-bucket/template.json --image us-central1-docker.pkg.dev/sofe4630/dataflow-docker/pedestrian_occlusion:latest --sdk-language PYTHON --metadata-file metadata.json

deploy the dataflow job (put your bucket and project name)
----------------------------------------------------------

gcloud dataflow flex-template run depth-test8 --template-file-gcs-location gs://sofe4630-bucket/template.json --region us-central1 --parameters project=sofe4630 --parameters temp_location=gs://sofe4630-bucket/temp --parameters sdk_container_image=us-central1-docker.pkg.dev/sofe4630/dataflow-docker/pedestrian_occlusion:latest --parameters streaming=true --parameters num_workers=1 --parameters autoscaling_algorithm=NONE