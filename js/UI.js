async function displayCSV(csvData) {
    /*
     * Display the CSV as an HTML grid
     * The table treats header row cells separately from the rest of the cells,
     * adding multiple listeners to handle UI components
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

        // Is the cell selected?
        let isSelected = selected[headerIndex];
        if (isSelected) {
            cell.style.backgroundColor = "#A9A9A9";
        }

        /*
        Add three listeners:
        1. Mouseover: Update the display box to show the header text
        2. Mouseout: Clear the display box
        3. Click: Index queryMap with the header's text and flip the value
           on/off. Then re-compile the form
        */
        cell.addEventListener("mouseover", () => {
            let cellText = cell.getAttribute("text-data");
            updateHeaderCellText(cellText);
        });
        cell.addEventListener("mouseout", () => {
            updateHeaderCellText("");
        });
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

