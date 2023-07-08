#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np

from acorn import Block

app = Flask(__name__)
cors = CORS(app)

def csv2dtm(csv: str) -> np.matrix:
    """Convert the stringified CSV into a matrix.

    Parameters
    ----------
    csv
        Stringified CSV (only data rows)

    Returns
    -------
    data
        The array
    """
    csv = json.loads(csv)
    data = csv['data']
    data = [[val for val in row.values()] for row in data]
    data = np.asmatrix(data, dtype=int)

    return data

def format_query(Q: str) -> np.ndarray:
    """Convert the query to an array of 0s and 1s.

    Parameters
    ----------
    Q
        Stringified version of the query

    Returns
    -------
    Q
        One-hot encoded query
    """
    Q = json.loads(Q)
    Q = np.asarray(Q, dtype=int)

    return Q

@app.route('/process-form', methods=['POST'])
def process_form() -> None:
    """Process the form data.
    
    There are three form fields:
    1. CSV data
    2. A query
    3. A normalization value
    """
    # Get the form data
    dtm = csv2dtm(request.form.get('csvData'))
    Q = format_query(request.form.get('query'))
    norm_by = float(request.form.get('normBy'))

    # Set up a block and query it
    block = Block(dtm)
    A = block.query(Q, norm_by)
    A ,= A.tolist()

    # Send the response back
    response = {
        'status': 'success'
        , 'associations': A
    }

    return jsonify(response)

if __name__ == '__main__':
    app.run()

