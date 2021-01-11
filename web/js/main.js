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

function setupRowButtons() {
    $(".fav-button, .rej-button").click(function() {
        var is_fav = $(this).hasClass("fav-button");
        var message = "Moved to Rejected";
        var typeClass = "rej-row";
        if(is_fav) {
            message = "Moved to Favorites";
            typeClass = "fav-row";
        }
        const undo_row = `
            <tr class="undo-row ${typeClass}">
                <td colspan="8"><strong><i>${message} - </i></strong></td>
                <td>
                    <div class="btn-group btn-group-xs" role="group" aria-label="...">
                        <button type="button" class="undo-button btn btn-warning">Undo</button>
                    </div>
                </td>
            </tr>
        `;
        deactivateUndoRows($(this).closest("table"));
        $(this).closest("tr").replaceWith(undo_row);
    });
}

function removeUndoRows(table) {

    $(table).find("tbody > tr").each(function() {
        if($(this).hasClass("undo-row")) {
            $(this).remove();
        }
    });
}

function deactivateUndoRows(table) {
    $(table).find("tbody > tr").each(function() {
        if($(this).hasClass("undo-row")) {
            var is_fav = $(this).hasClass("fav-row");
            var message = "Moved to Rejected";
            if(is_fav)
                message = "Moved to Favorites";
            const undo_row = `
                <td colspan="9"><i>${message}</i></td>
            `;
            $(this).html(undo_row);
        }
    });
}


window.addEventListener('pywebviewready', () => {
    pywebview.api.ready().then(showResponse);
});

window.onload = function(e) {
    // Load the latest scrape data
    $("#master-error-alert").hide();
    $("#address-table").hide();

    $("#address-table > thead > tr > th.sortable-col > a").click(function() {
        let sort_column_idx = $("#address-table > thead > tr > th.sortable-col").toArray().indexOf($(this).parent()[0]);
        table = $(this).closest("table");
        removeUndoRows(table);
        items = $(table).find("tbody > tr").toArray();
        desc = $(table).prop("desc");
        // Sort remaining rows
        items.sort( function(a, b) {
            data_a = $(a).find("td")[sort_column_idx];
            data_b = $(b).find("td")[sort_column_idx];
            return $(data_a).text().localeCompare($(data_b).text());
        });
        if(desc == true) {
            $(table).prop("desc", false);
            $(table).find("tbody").html($(items.reverse()));
        }
        else {
            $(table).prop("desc", true);
            $(table).find("tbody").html($(items));
        }
        setupRowButtons();
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
                        <td class="address-row">${item["address"]}</td>
                        <td>$${item["rent"]}</td>
                        <td>${(item["beds"] ? item["beds"] : "--")}</td>
                        <td>${(item["baths_str"] ? item["baths_str"] : "--")}</td>
                        <td>${train_elements}</td>
                        <td><span class="progress-bar-${color} badge">${(char_data["score"] * 100.0).toFixed(2)}</span></td>
                        <td>${item["source"]}</td>
                        <td><a target="_new" href='${item["link"]}'>Visit Page<a/></td>
                        <td>
                            <div class="btn-group btn-group-xs" role="group" aria-label="...">
                                <button type="button" class="fav-button btn btn-success">Favorite</button>
                                <button type="button" class="rej-button btn btn-danger">Reject</button>
                            </div>
                        </td>
                    </tr>
                `;
                $("tbody#address-table-body").append(table_row);
            }
            else
                console.log("Missing characterization data for '" + item["address"] + "'");
        });
        $("#address-table").show();

        setupRowButtons();
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