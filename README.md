# tandem-dimple-app

Webapp for Tandem-dimple project

## Installation

First, clone the repo and the submodule (Tandem-Dimple)

```bash
git clone <path_to_git>
git submodule update --init
```

We need to first have the environment to download the database. This is used by Loci's downloading script.

```bash
conda env create -f environment_for_downloading_database.yml
```

Then, we can download the required database for Loci's inference code

```bash
conda activate tandem

# In ./inference/external_infer/
bash scripts/download_pfam.sh data/pfamdb # 1.5G, ~1.5m
bash scripts/download_consurf_db.sh data/consurf/db # 2.5G, ~2m
# Please skip this database for now
# We will download this database later
bash scripts/download_uniref90.sh data/consurf # 90G, ~127m
```

Then, we can build and run the docker containers.

```bash
# Build and run all the containers
docker compose up -d --build

# Stop all containers
docker compose down
```

We can check the frontend at http://0.0.0.0:7860/

## Database

* ```user_input```

    Its status would go from ```pending``` -> ```processing``` -> ```finished```

## What each docker does?

* ```gradio_app```

    Frontend for the website, exposed on port 7860.

    Would check for and update the result from the database automatically, for every 3 seconds.

* ```mongodb```

    Database

    container platform: ```linux/amd64``` or ```linux/arm64``` both are OK, very stable. But don't use ```linux/amd64``` on Apple Silicon, since Rosetta does not have CPU AVX support.

* ```worker```

    Automatically fetch user input one-by-one, whose "status" are "pending".

    Use atomically lock jobs, whenever an input is fetched, its "status" changes from "pending" -> "processing"

    Jsonify the input and send to the inference container docker, through HTTP API.

    Write the input with the results, back to database, "status" changed from "processing" to "finished".

* ```inference```

    Perform feature processing and model inference.

    The inference docker build the correct environment needed for Loci's inference code.

    Container platform can only use ```linux/amd64```, and cannot run on Apple Silicon, since TensorFlow needs CPU AVX support.

    Serve a ```/infer``` API through flask, on internal port 5000.

    Use git submodule to link to Loci's inference git repo.

    Use ```adapter.py``` to import Loci's inference functions.