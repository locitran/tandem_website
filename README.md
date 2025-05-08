# tandem-dimple-app

Webapp for Tandem-dimple project

## What each docker does?

* ```gradio_app```

    Frontend for the website.

* ```mongodb```

    Database

* ```worker```

    Automatically fetch user input one-by-one, whose "status" are "pending".

    Use atomically lock jobs, whenever an input is fetched, its "status" changes from "pending" -> "processing"

    Jsonify the input and send to the inference container docker, through HTTP API.

    Write the input with the results, back to database, "status" changed from "processing" to "finished".

* ```inference```

    Perform feature processing and model inference.

    Serve a ```/infer``` API through flask.

    This should be changed Loci's docker container.