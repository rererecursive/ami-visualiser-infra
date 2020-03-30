"""
PUT/LOAD:

Extract the necessary information from the files in S3:
    - manifest.json
    - ohai.json
    - output.log
    - source-ami.json
    - produced-ami.json
and load it into DynamoDB.

Loading will be done via an S3 event which triggers Lambda.

Loading should convert the parent AMI ID to the key ID in Dynamo. This ensures that the data is in a 'purely readable state', requiring no modifications when read.
"""

"""
GET (API):

Request the data from Dynamo.
"""
import json
import time
import os
import boto3
import zipfile

region  = os.environ['REGION']
table   = os.environ['TABLE']
dynamo_client = boto3.client('dynamodb', region_name=region)
ec2_client    = boto3.client('ec2', region_name=region)
s3_client     = boto3.client('s3', region_name=region)

def lambda_handler(event, context):
  record  = event['Records'][0]
  bucket  = record['s3']['bucket']['name']
  key     = record['s3']['object']['key']
  folder  = ''.join(key.rpartition('/')[:-1]) # 'x/y/z' -> 'x/y/'
  ami     = AMI()
  amis    = []
  files   = {}

  # print("Waiting 5 seconds for other files to be uploaded...")
  # time.sleep(5)

  # Process each file in the S3 folder.
  files = fetch_files_from_s3(bucket, folder, ami.get_files())
  ami.process_files(files)

  # Confirm the source (parent) AMI exists in DynamoDB as well.
  new_parent_ami = get_parent_ami_to_add(ami, files['source-ami.json'])
  if new_parent_ami:
    print(f"Parent AMI '{new_parent_ami.schema['id']}' will be added to the table.")
    amis.append(new_parent_ami)
  else:
    print("Parent AMI already exists in table.")

  amis.append(ami)

  # Convert and send the items to DynamoDB.
  for i,a in enumerate(amis):
    item = a.to_dynamodb_schema()
    print(f"Adding the following item to table '{table}' ...")
    print(json.dumps(item))
    dynamo_client.put_item(
      TableName=table,
      Item=item
    )


def fetch_files_from_s3(bucket, folder, filenames):
  files = {}
  build_zip = 'build.zip'

  print(f"Fetching '{build_zip}' from:")
  print(f"  S3 bucket: {bucket}")
  print(f"  S3 folder: {folder}")

  os.chdir('/tmp')
  s3_client.download_file(
    Bucket=bucket,
    Key=folder + build_zip,
    Filename=build_zip
  )

  with zipfile.ZipFile(build_zip, 'r') as zip_ref:
    zip_ref.extractall('.')

  for file in filenames:
    print(f"Reading {file} ...")
    with open(file) as fh:
      data = fh.read()

    if file.endswith('.json'):
      data = json.loads(data)

    files[file] = data

  return files

def get_parent_ami_to_add(ami, parent_data):
  """Ensure that parent AMIs exist in the table.
  If they don't, create an AMI object for each of them.

  The produced image's parent is provided in the file. Subsequent parents
  must be queried for.
  """
  parent_ami = None
  parent = ami.schema['parent']
  parent_item = dynamo_client.get_item(TableName=table, Key={"id": {"S":parent}})

  if 'Item' not in parent_item:
    parent_ami = AMI()
    parent_ami.add_ami_details(parent_data)

  return parent_ami
"""
Each Dynamo record is a document describing the AMI.
It links to other data via a "parent".
A parent is an AMI ID that must be resolved to an integer by querying Dynamo.
This is the only transformation required before storing the document into Dynamo.
"""

class AMI:
  def __init__(self):
    self.schema = {
      'id':         '',
      'parent':     'unknown',
      'download':   {},
      'languages':  {},
      'packages':   {},
      'summary':    {},
      # 'tags':       [],
    }
    self.processors = {
      # 'manifest.json':      [],
      'ohai.json':          [self.add_packages, self.add_languages, self.add_system_info],
      # 'output.log':         [],
      'produced-ami.json':  [self.add_ami_details],
      'source-ami.json':    [self.add_source_ami_details]
      # 'packer.json':        [self.add_bake_details]
    }

  def get_files(self):
    return list(self.processors.keys())

  def process_files(self, files):
    for filename, contents in files.items():
      funcs = self.processors[filename]

      for fn in funcs:
        fn(contents)

  def add_source_ami_details(self, details):
    """Lookup the AMI ID from DynamoDB. If it does not exist, we'll
    need to create it using this same object.
    """
    self.schema['parent'] = details['ImageId']

  def add_ami_details(self, details):
    keys_to_keep = ['CreationDate', 'OwnerId', 'Description', 'Name']
    items = {k:v for k,v in details.items() if k in keys_to_keep}

    self.schema['summary'].update(items)
    self.schema['id'] = details['ImageId']

  def add_bake_details(self, details):
    """Add to the summary the Git details, Packer version, Chef recipe
    that came from the bake.
    """
    pass

  def add_packages(self, dct):
    """Add package information (Chef, Docker).
    """
    packages = {'Docker':'docker.io'}

    for k,v in packages.items():
      if v in dct['packages']:
        version = dct['packages'][v]
        self.schema['packages'].update({k:version})

  def add_languages(self, dct):
    """Add language information (Ruby, Python, etc).
    """
    languages = {k.capitalize():v['version'] for k,v in dct['languages'].items()}
    self.schema['languages'].update(languages)

  def add_system_info(self, dct):
    """Add system information (OS, kernel).
    """
    self.schema['summary'].update(
      {
        'Kernel': dct['hostnamectl']['kernel'],
        'OperatingSystem': dct['hostnamectl']['operating_system']
      }
    )

  def lookup_source_ami_id(self):
    """Query DynamoDB for the AMI's ID.
    """
    pass

  def to_dynamodb_schema(self, input=None):
    output = {}
    if input is None:
      input = self.schema

    for key, value in input.items():
      if type(value) == str:
        output[key] = {'S': value}

      elif type(value) == dict:
        items = self.to_dynamodb_schema(value)
        output[key] = {'M': items}

    return output
