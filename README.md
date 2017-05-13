# spark-gcp-babelfish
Spark Room Babelfish "bot" backed by Google Cloud Platform's Translate API

# Requirements
In order to use this software, you must have a Spark account, Spark Token and Google Cloud Platform
credentials.
- Go to Spark for Developers at developer.ciscospark.com to create an account and get a token
- Go to the GCP Auth Guide at https://cloud.google.com/docs/authentication for more information on obtaining a "Server-centric authentication" instructions, namely establishing a service account.
- Additionally, you will need to enable the GCP Translate APIs in the project you establish for this software.
- Python 3 environment that has Google Cloud APIs available, specifically
  - google-cloud-translate
  - google-api-python-client 

# Caveat
Note: I personally use Continuum's Anaconda python distribution for this
development - for no good reason other than I use it for other projects that
it is essential for.  Using native Python virtualenv should work just fine
but YMMV.

# Usage
1. Create a new Python environment
 - conda create -n spark-gcp 
 - source activate spark-gcp
2. Install Google pip modules
 - pip install -y google-cloud-translate
 - pip install -y google-api-python-client 
3. Get Spark Token information
4. Generate GCP service account JSON file, set environment variable GOOGLE_APPLICATION_CREDENTIALS appropriately
5. Check out code from GitHub - can be done anywhere
 - cd ${HOME}
 - git clone https://github.com/gve-vse-tim/spark-gcp-babelfish.git
6. Update the config.py file with the Spark Token info
7. For a super quick demo, simply run the demo.sh script

