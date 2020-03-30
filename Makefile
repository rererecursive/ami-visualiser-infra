AWS_S3_BUCKET	?= ztlewis-builds
AWS_S3_PREFIX	?= lambdas
AWS_APPLICATION ?= amis
SHELL 		:= /bin/bash
GIT_BRANCH 	:= $(shell git rev-parse --abbrev-ref HEAD)
GIT_COMMIT 	:= $(shell git rev-parse --short HEAD)
VERSION 	:= $(GIT_BRANCH)-$(GIT_COMMIT)

## Stack parameters must be prefixed with '_PARAM_':
#_PARAM_StackParam1=Yes
#_PARAM_StackParam2=No
PARAMS := $(foreach v, $(filter _PARAM_%,$(.VARIABLES)), $(v)=$($(v)))

create: clean lambda-package generate-parameters cfn-package

update: clean lambda-package generate-parameters cfn-package cfn-update status

lambda-package:
	@cd functions && zip -r src.zip * && mv src.zip .. && cd ..
	@echo -n ${VERSION}- > functions.version && sha256sum src.zip | head -c 16 >> functions.version
	aws s3 cp src.zip s3://${AWS_S3_BUCKET}/${AWS_S3_PREFIX}/$$(cat functions.version)/src.zip
	@echo LambdaFunctionsVersion=$$(cat functions.version) > envvars

# This depends on 'lambda-package' to have run.
generate-parameters:
	@sed -i 's/^/_PARAM_/g' envvars
	@set -a && source envvars && set +a && ${PARAMS} jq -n '[env | to_entries[] | select(.key | startswith("_PARAM_")) |  {"ParameterKey":(.key | sub("_PARAM_";"")), "ParameterValue":.value}]' > new.json
	@aws cloudformation describe-stacks \
		--stack-name ${AWS_APPLICATION} \
		--query 'Stacks[0].Parameters' > current.json
	@jq '[.[] | .["UsePreviousValue"] = true | del(.ParameterValue)]' current.json > current.json.temp
	@jq -s '[ .[0] + .[1]  | group_by(.ParameterKey)[] | last ]' current.json.temp new.json > parameters.json

# 'gem install cfhighlander'
cfn-package:
	cfhighlander cfpublish \
		--dstbucket ${AWS_S3_BUCKET} \
		--dstprefix ${AWS_S3_PREFIX} \
		--validate \
		${AWS_APPLICATION}

cfn-update:
	@echo "Updating stack: ${AWS_APPLICATION} ..."
	@aws cloudformation update-stack \
		--stack-name ${AWS_APPLICATION} \
		--template-url https://${AWS_S3_BUCKET}.s3.amazonaws.com/${AWS_S3_PREFIX}/latest/${AWS_APPLICATION}.compiled.yaml \
		--capabilities CAPABILITY_IAM \
		--parameters file://parameters.json

status:
	@aws cloudformation describe-stacks \
		--stack-name ${AWS_APPLICATION} \
		--query 'Stacks[0].{Name:StackName,Status:StackStatus,LastUpdated:LastUpdatedTime}'

init-db:
	aws dynamodb put-item --table-name ${TABLE_NAME} --item '{"id": {"S": "unknown"}}'

clean:
	rm -rf *.json* envvars functions.version src.zip out
