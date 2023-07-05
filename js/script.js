const URL = "http://localhost:5000/process-form";

async function loadCSV(csvURL) {
    /*
     * Load a CSV
     * Returns a Papa Parse CSV object
     * @param {string} csvURL - Location of the CSV
     */
    var response = await fetch(csvURL);
    var csvData = await response.text();

    return Papa.parse(csvData, { header: true });
}

function makeQueryMap(csvData) {
    /*
     * Build the query map
     * Returns a query map of {headerCell : false} values
     * @param {Object} csvData - Papa Parse CSV
     */
    var queryMap = {}
    var headers = csvData.meta.fields;
    headers.forEach((header) => {
        queryMap[header.trim()] = false;
    });

    return queryMap;
}

async function displayCSV(csvData) {
    /*
     * Display the CSV as an HTML grid
     * The table treats header row cells separately from the rest of the cells,
     * adding a listener for each one that flips its associated queryMap value
     * on/off
     * @param {Object} csvData - Papa Parse CSV
     */
    var headers = csvData.meta.fields;
    var data = csvData.data;

    // Access the grid container and clear it
    var container = document.getElementById("dtmContainer");
    container.innerHTML = "";

    // Find the number of columns for the grid
    var numCols = headers.length;
    container.style.gridTemplateColumns = `repeat(${numCols}, minmax(5%, 1fr))`;

    // Retrieve the values of queryMap. We use these to determine whether or
    // not a header cell should be highlighted
    var selected = Object.values(queryMap);

    // Create the header cells
    headers.forEach((header, headerIndex) => {
        // Build a cell and give it an attribute for the text data. This will
        // be displayed in a div to the right of the CSV
        let cell = document.createElement("div");
        cell.classList.add("header-cell");
        cell.setAttribute("text-data", header.trim());

        // Add listeners to communicate with the display box, which shows text
        // of the headers
        cell.addEventListener("mouseover", () => {
            let cellText = cell.getAttribute("text-data");
            updateHeaderCellText(cellText);
        });
        cell.addEventListener("mouseout", () => {
            updateHeaderCellText("");
        });

        // Is the cell selected?
        let isSelected = selected[headerIndex];
        if (isSelected) {
            cell.style.backgroundColor = "#D3D3D3";
        }

        // Add another listener, which flips the associated queryMap value
        // on/off and re-compiles the form
        cell.addEventListener("click", () => {
            let cellText = cell.getAttribute("text-data");
            queryMap[cellText] = !queryMap[cellText];
            compileForm();
            updateTermsDisplayed();
        });
        container.appendChild(cell);
    });

    // Create the data cells
    data.forEach((row, rowIndex) => {
        Object.values(row).forEach((value) => {
            let cell = document.createElement("div");
            cell.classList.add("data-cell");
            cell.textContent = value;
            let alpha = docAssoc[rowIndex];
            cell.style.backgroundColor = `rgba(160, 32, 240, ${alpha})`;
            container.appendChild(cell);
        });
    });
}

function scaleAssociations(docAssoc) {
    /*
     * Scale the document associations to a [0,1] range
     * Returns scaled document associations
     * @param {Array} docAssoc - Document associations
     */
    let min = Math.min(...docAssoc);
    let max = Math.max(...docAssoc);
    docAssoc = docAssoc.map((value) => (value - min) / (max - min));

    // Exacerbate differences between the values
    docAssoc = docAssoc.map((value) => Math.pow(value, 3));

    return docAssoc;
}

function updateHeaderCellText(text) {
    /*
     * Update the header cell display
     * @param {String} text - Text to display
     */
    var displayBox = document.getElementById("header-display");
    displayBox.textContent = text;
}

function updateTermsDisplayed() {
    /*
     * Update the selected terms list by referencing `queryMap`
     */
    var termsDisplayed = document.getElementById("terms-displayed");
    for (header in queryMap) {
        // Look to see if we already have an element. If so, delete it
        let listEntry = document.getElementById(`${header}-select`);
        if (listEntry) {
            termsDisplayed.removeChild(listEntry);
        }

        // If the entry is in the query, add it to the list
        if (queryMap[header]) {
            let newEntry = document.createElement("li");
            newEntry.setAttribute("id", `${header}-select`);
            newEntry.textContent = header;
            termsDisplayed.appendChild(newEntry);
        }
    }
}

function submitForm(formData) {
    /*
     * POST the form data to the Flask API
     * Form data contains fields for normBy, csvData, and query
     * @param {Object} formData - The form data
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


