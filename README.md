ACORN
=====

Description and demos to come. For now, here's the original:

![The original ACORN system](docs/acorn_original.png)

And here's a screenshot of the implementation:

![An example document-term matrix displayed with ACORN](docs/acorn_new.png)

Installation
------------

There are two separate parts to installation. The first part installs code that
implements ACORN itself, while the second sets up an app for working
interactively with the network.

### ACORN

Besides the ACORN source files in `src/`, all dependencies are managed with
conda; the conda environment file is `env.yml`. Once you have cloned this
repository, go through the following steps.

Steps

1. Install the conda environment
   ```sh
   conda env create --name acorn --file=env.yml
   ```
2. Activate the environment
   ```sh
   conda activate acorn
   ```
3. Install ACORN via pip (ensure you do so from the top of the repository)
   ```sh
   pip install .
   ```

### Web App

The web app uses a Flask API to send query information and receive document
associations. It requires you to have a web server running. Flask will serve
from port 5000.

Steps

1. Move this repository to wherever your computer serves websites.
   Alternatively, [use Python][pyweb] (and a terminal multiplexer) to run a
   server directly from here
2. From the root of the repository, create a new directory called `assets/` and
   a subdirectory therein, `data/`
   ```sh
   mkdir assets
   mkdir assets/data
   ```
3. Download the [JS dependencies](#app-dependencies) and the [font file as well
   as some sample data][data]. Place everything but the data into `assets/`.
   Put the data in `assets/data`
4. Activate the environment and start the app
   ```sh
   conda activate acorn
   python3 src/main.py
   ```
5. In a web browser, navigate to http://localhost/ACORN. The app should be
   displayed there

[pyweb]: https://realpython.com/python-http-server
[data]: http://tylershoemaker.info/data/ACORN

### App Dependencies

The app requires two external JS libraries, which should be placed in `assets/`
(see step 2 above). If needed, see the header section in `index.html` for
filenames

1. [Papa Parse (minified)](https://www.papaparse.com)
2. [input-knob.js](https://g200kg.github.io/input-knobs/)
