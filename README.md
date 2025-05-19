# tandem-dimple-app

Webapp for Tandem-dimple project

## Database

* ```user_input```

    Its status would go from ```pending``` -> ```processing``` -> ```finished```

## What each docker does?

* ```gradio_app```

    Frontend for the website.

    Would check for and update the result from the database automatically, for every 3 seconds.

* ```mongodb```

    Database

    container platform: ```linux/amd64``` or ```linux/arm64``` both are OK, very stable. But don't use ```linux/amd64``` on Apple Silicon, since Rosetta does not have CPU AVX support/

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