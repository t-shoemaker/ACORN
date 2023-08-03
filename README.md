ACORN
=====

Description and demos to come. For now, here's the original:

![The original ACORN system](docs/acorn_original.png)

And here's a screenshot of the implementation:

![An example document-term matrix displayed with ACORN](docs/acorn_new.png)

### Installing the web app

The web app version of ACORN uses a Flask API to send query information and
receive document associations. All Python libraries are managed with conda; the
conda environment file is `env.yml`.

The app also requires you to have a web server running. Flask will serve from
port 5000.

Steps

1. Move this repository to wherever your computer serves websites
2. From the root of the repository, create a new directory called `assets/` and
   a subdirectory therein, `data/`
   ```sh
   mkdir assets
   mkdir assets/data
   ```
3. Download the [JS dependencies](#dependencies) and the [font file as well as
   some sample data][data]. Place everything but the data into `assets/`. Put
   the data in `assets/data`
4. Install the conda environment
   ```sh
   conda env create --name envname --file=env.yml
   ```
5. Activate the environment
   ```sh
   conda activate acorn
   ```
6. Start the app
   ```sh
   python3 src/main.py
   ```
7. In a web browser, navigate to http://localhost/ACORN. The app should be
   displayed there

[data]: http://tylershoemaker.info/data/ACORN

### Dependencies

The app requires two external JS libraries, which should be placed in `assets/`
(see step 2 above). If needed, see the header section in `index.html` for
filenames

1. [Papa Parse (minified)](https://www.papaparse.com)
2. [input-knob.js](https://g200kg.github.io/input-knobs/)
