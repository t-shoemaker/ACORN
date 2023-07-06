// Global parameters
let csvData;
let queryMap = {};
let docAssoc = [];
const URL = "http://localhost:5000/process-form";

async function loadCSV(csvURL) {
    /*
     * Load a CSV
     * @param {String} csvURL - Location of the CSV
     * @return {Object} csv - Papa ParseCSV
     */
    var response = await fetch(csvURL);
    var csvData = await response.text();

    return Papa.parse(csvData, { header: true });
}

function makeQueryMap(csvData) {
    /*
     * Build the query map
     * @param {Object} csvData - Papa Parse CSV
     * @return {Map} queryMap - Query map of {headerCell : false} values
     */
    var queryMap = {}
    var headers = csvData.meta.fields;
    headers.forEach((header) => {
        queryMap[header.trim()] = false;
    });

    return queryMap;
}

function scaleAssociations(docAssoc, exp = 3) {
    /*
     * Scale the document associations to a [0,1] range
     * @param {Array} docAssoc - Document associations
     * @param {Number} exp - Exponent by which to scale the associations
     * @return {Array} scaledDA - Scaled document associations
     */
    var min = Math.min(...docAssoc);
    var max = Math.max(...docAssoc);
    var scaledDA = docAssoc.map((value) => (value - min) / (max - min));

    // Exacerbate differences between the values
    scaledDA = scaledDA.map((value) => Math.pow(value, exp));

    return scaledDA;
}

function compileForm() {
    /*
     * This is a simple helper function that adds the CSV data and
     * query to the form before sending everything to the API
     */
    var formData = new FormData(form);
    formData.append("csvData", JSON.stringify(csvData));
    formData.append("query", JSON.stringify(Object.values(queryMap)));
    submitForm(formData);
}

function submitForm(formData) {
    /*
     * POST the form data to the Flask API
     * Form data contains fields for normBy, csvData, and query
     * @param {Object} formData - The form data
     * @return {Object} responseData - Document associations from the API
     */
    fetch(URL, {
        method: "POST"
        , body: formData
    })
    .then(response => response.json())
    .then(responseData => {
        // Upon receiving a response, get the document associations and
        // reassign `docAssoc`. Display the CSV with the new association values
        docAssoc = scaleAssociations(responseData['associations']);
        displayCSV(csvData);
    })
    .catch(error => {
        console.log("Error:", error);
    });
}


