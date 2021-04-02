#
# Janky front-end to bring some sanity (?) to the litany of tools and switches
# in setting up, tearing down and validating your Minikube cluster for working
# with k8s and istio.
#
# This file covers off building the Docker images and optionally running them
#
# The intended approach to working with this makefile is to update select
# elements (body, id, IP, port, etc) as you progress through your workflow.
# Where possible, stodout outputs are tee into .out files for later review.
#
# Switch to alternate container registry by setting CREG accordingly.
#
# This script is set up for Github's newly announced (and still beta) container
# registry to side-step DockerHub's throttling of their free accounts.
# If you wish to switch back to DockerHub, CREG=docker.io
#
# TODO: You must run the template processor to fill in the template variables "ZZ-*"
#

CREG=ZZ-CR-ID
REGID=scp-2021-jan-cmpt-756

DK=docker

# Keep all the logs out of main directory
LOG_DIR=logs

all: s1 s2 s3 db

deploy: s1 s2 s3 db
	$(DK) run -t --publish 30001:30001 --detach --name landlord $(CREG)/$(REGID)/team-a-service-landlord:v1 | tee landlord.svc.log
	$(DK) run -t --publish 30002:30002 --detach --name property $(CREG)/$(REGID)/team-a-service-property:v1 | tee property.svc.log
	$(DK) run -t --publish 30003:30003 --detach --name tenant $(CREG)/$(REGID)/team-a-service-tenant:v1 | tee tenant.svc.log
	$(DK) run -t \
		-e AWS_REGION="ZZ-AWS-REGION" \
		-e AWS_ACCESS_KEY_ID="ZZ-AWS-ACCESS-KEY-ID" \
		-e AWS_SECRET_ACCESS_KEY="ZZ-AWS-SECRET-ACCESS-KEY" \
		-e AWS_SESSION_TOKEN="ZZ-AWS-SESSION-TOKEN" \
            --publish 30000:30000 --detach --name teamadb $(CREG)/$(REGID)/team-a-teamadb:v1 | tee teamadb.svc.log

scratch:
	$(DK) stop `$(DK) ps -a -q --filter name="teamadb"` | tee teamadb.stop.log
	$(DK) stop `$(DK) ps -a -q --filter name="landlord"` | tee landlord.stop.log
	$(DK) stop `$(DK) ps -a -q --filter name="property"` | tee property.stop.log
	$(DK) stop `$(DK) ps -a -q --filter name="tenant"` | tee tenant.stop.log

clean:
	rm $(LOG_DIR)/{landlord, property, tenant,teamadb}.{img,repo,svc}.log

s1: $(LOG_DIR)/landlord.repo.log

s2: $(LOG_DIR)/property.repo.log

s3: $(LOG_DIR)/tenant.repo.log

db: $(LOG_DIR)/teamadb.repo.log

$(LOG_DIR)/landlord.repo.log: ../code/service-landlord/app.py ../code/service-landlord/Dockerfile
	
	$(DK) build -t $(CREG)/$(REGID)/team-a-service-landlord:v1 ../code/service-landlord | tee $(LOG_DIR)/landlord.img.log
	#$(DK) push $(CREG)/$(REGID)/team-a-service-landlord:v1 | tee $(LOG_DIR)/landlord.repo.log

$(LOG_DIR)/property.repo.log: ../code/service-property/app.py ../code/service-property/Dockerfile
	
	$(DK) build -t $(CREG)/$(REGID)/team-a-service-property:v1 ../code/service-property | tee $(LOG_DIR)/property.img.log
	#$(DK) push $(CREG)/$(REGID)/team-a-service-property:v1 | tee $(LOG_DIR)/property.repo.log

$(LOG_DIR)/tenant.repo.log: ../code/service-tenant/app.py ../code/service-tenant/Dockerfile
	
	$(DK) build -t $(CREG)/$(REGID)/team-a-service-tenant:v1 ../code/service-tenant | tee $(LOG_DIR)/tenant.img.log
	#$(DK) push $(CREG)/$(REGID)/team-a-service-tenant:v1 | tee $(LOG_DIR)/tenant.repo.log

$(LOG_DIR)/teamadb.repo.log: ../code/db/Dockerfile
	$(DK) build -t $(CREG)/$(REGID)/team-a-teamadb:v1 ../code/db | tee $(LOG_DIR)/teamadb.img.log
	#$(DK) push $(CREG)/$(REGID)/team-a-teamadb:v1 | tee $(LOG_DIR)/teamadb.repo.log
