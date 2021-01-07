/*
    PyAgent - Python program for aggregating housing info
    Copyright (C) 2021 Timothy Volpe

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

const DATA_FILE = "data/scraped_data.json"
const CHAR_FILE = "data/characterization.json"

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function showResponse(response) {
    if( response != null)
        console.log(response.message);
}

function postErrorAlert(message) {
    $("#master-error-alert").append("<p>" + message + "</p>");
    $("#master-error-alert").show();
}

window.addEventListener('pywebviewready', () => {
    pywebview.api.ready().then(showResponse);
});

window.onload = function(e) {
    // Load the latest scrape data
    $("#master-error-alert").hide();
    $("#address-table").hide();

    $("#address-table > thead > tr > th > a").click(function() {
        console.log("Sort header");
    });
};

var json_housing_data = null;
var json_char_data = null;
function finished_json_load(housing_json, char_json)
{
    if( housing_json !== null ) {
        json_housing_data = housing_json;
    }
    if( char_json !== null ) {
        json_char_data = char_json;
    }
    if(json_housing_data !== null && json_char_data !== null)
    {
        json_housing_data.forEach(function(item) {
            char_data = json_char_data[item["uid"]];
            if( char_data ) {
                // Determine score color
                var color = "";
                if( char_data["score"] < 0.33 ) {
                    color = "danger";
                }
                else if( char_data["score"] < 0.66 && char_data["score"] > 0.33 ) {
                    color = "warning";
                }
                else {
                    color = "success";
                }
                // Get trains
                var train_elements = "";
                if( char_data["trains"] ) {
                    for( var key in char_data["trains"] ) {
                        if( key == "Green Line (main)" )
                            train_elements += "<span class='train-green badge'>&nbsp;</span>";
                        else if( key == "Green Line (B)" )
                            train_elements += "<span class='train-green badge'>B</span>";
                        else if( key == "Green Line (C)" )
                            train_elements += "<span class='train-green badge'>C</span>";
                        else if( key == "Green Line (D)" )
                            train_elements += "<span class='train-green badge'>D</span>";
                        else if( key == "Green Line (E)" )
                            train_elements += "<span class='train-green badge'>E</span>";
                        else if( key == "Blue Line" )
                            train_elements += "<span class='train-blue badge'>&nbsp;</span>";
                        else if( key == "Orange Line" )
                            train_elements += "<span class='train-orange badge'>&nbsp;</span>";
                        else if( key == "Orange Line" )
                            train_elements += "<span class='train-orange badge'>&nbsp;</span>";
                        else if( key == "Red Line (main)" )
                            train_elements += "<span class='train-red badge'>&nbsp;</span>";
                        else if( key == "Red Line (Braintree)" )
                            train_elements += "<span class='train-red badge'>B</span>";
                        else if( key == "Red Line (Ashmont)" )
                            train_elements += "<span class='train-red badge'>A</span>";
                        else if( key == "Red Line (Mattapan)" )
                            train_elements += "<span class='train-red badge'>M</span>";
                        else if( key == "Commuter Rail")
                            train_elements += "<span class='train-commuter badge'>&nbsp;</span>";
                        else if( key == "Silver Line")
                            train_elements += "<span class='train-silver badge'>&nbsp;</span>";
                        else
                            console.log("Unknown train line: " + key)
                    }
                }
                // Add row
                var table_row = `
                    <tr>
                        <th scope="row">${item["address"]}</th>
                        <td>$${item["rent"]}</td>
                        <td>${(item["beds"] ? item["beds"] : "--")}</td>
                        <td>${(item["baths_str"] ? item["baths_str"] : "--")}</td>
                        <td>${train_elements}</td>
                        <td><span class="progress-bar-${color} badge">${(char_data["score"] * 100.0).toFixed(2)}</span></td>
                        <td>${item["source"]}</td>
                        <td><a target="_new" href='${item["link"]}'>Visit Page<a/></td>
                    </tr>
                `;
                $("tbody#address-table-body").append(table_row);
            }
            else
                console.log("Missing characterization data for '" + item["address"] + "'");
        });
        $("#address-table").show();
    }
}

function load_json(housing_avail=true, char_avail=true) {
    if(housing_avail)
    {
        $.getJSON(DATA_FILE, function(json_house) {
            finished_json_load(json_house, null);
        });
        if(char_avail) {
            $.getJSON(CHAR_FILE, function(json_char) {
                finished_json_load(null, json_char);
            });
        }
    }
    else {
        postErrorAlert("There was no housing data! Run `pyagent.py -s` to scrape housing data.")
    }
}