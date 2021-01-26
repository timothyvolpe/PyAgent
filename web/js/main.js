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

let loaded_char_data = null;
let removed_char_data = {};
let orphaned_char_data = {};

const TableType = Object.freeze({"TableAll": 1, "TableFavorites": 2, "TableRejections": 3})

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function showResponse(response) {
    if( response != null)
        console.log(response.message);
}

function postErrorAlert(message) {
    console.log("ERROR: " + message)
    $("#master-error-alert").append("<p>" + message + "</p>");
    $("#master-error-alert").show();
}

function addToList(is_fav, hash, row, data, is_back_to_old=false)
{
    var message = "Moved to Rejected";
    var typeClass = "rej-row";
    if(is_back_to_old) {
        message = "Removed from list";
        typeClass = "remove-row";
        $(row).remove();
        return;
    }
    else {
        if(is_fav) {
            message = "Moved to Favorites";
            typeClass = "fav-row";
        }
    }

    const undo_row = `
        <tr class="undo-row ${typeClass}" hash="${hash}">
            <td colspan="9"><strong><i>${message} - ${data["housing_data"]["address"]}</i></strong></td>
            <td>
                <div class="undo-btn-group btn-group btn-group-xs" role="group" aria-label="...">
                    <button type="button ${typeClass}" class="undo-button btn btn-warning btn-sm">Undo</button>
                </div>
            </td>
        </tr>
    `;
    var row_element = $(undo_row);
    $(row_element).find(".undo-button").click(function() {
        var row = $(this).closest("tr");
        var hash = $(row).attr("hash");
        var data = removed_char_data[hash];

        if(is_fav) {
            pywebview.api.remove_from_favorites(hash);
        }
        else {
            pywebview.api.remove_from_rejections(hash);
        }

        var new_row = create_table_row(hash, data.char_output, data.housing_data);
        loaded_char_data[hash] = data;
        delete removed_char_data[hash];
        $(row).replaceWith(new_row);
        setupRowButtons();
        update_list_counts();
    });
    $(row).replaceWith(row_element);
}

function setupRowButtons() {
    $(".fav-button, .rej-button, .remove-button").click(function() {
        var is_fav = $(this).hasClass("fav-button");
        var is_remove = $(this).hasClass("remove-button");
        var row = $(this).closest("tr");
        var hash = $(row).attr("hash");
        var data;
        if(is_remove)
            data = removed_char_data[hash];
        else
            data = loaded_char_data[hash];

        if(is_remove)
        {
            //is_back_to_old
            if(is_fav) {
                pywebview.api.remove_from_favorites(hash).then(function(response) {
                    if(response) {
                        addToList(is_fav, hash, row, data, true);
                        loaded_char_data[hash] = removed_char_data[hash];
                        delete removed_char_data[hash];
                        update_list_counts();
                    }
                    else {
                        console.log("Cannot remove from favorites");
                    }
                });
            }
            else {
                pywebview.api.remove_from_rejections(hash).then(function(response) {
                    if(response) {
                        addToList(is_fav, hash, row, data, true);
                        loaded_char_data[hash] = removed_char_data[hash];
                        delete removed_char_data[hash];
                        update_list_counts();
                    }
                    else {
                        console.log("Cannot remove from rejections");
                    }
                });
            }
        }
        else {
            if(is_fav) {
                pywebview.api.add_to_favorites(hash, data).then(function(response) {
                    if(response) {
                        addToList(is_fav, hash, row, data);
                        removed_char_data[hash] = loaded_char_data[hash];
                        delete loaded_char_data[hash];
                        update_list_counts();
                    }
                    else {
                        console.log("Cannot add to favorites");
                    }
                }).catch(showResponse);

            }
            else {
                pywebview.api.add_to_rejections(hash, data).then(function(response) {
                    if(response) {
                        addToList(is_fav, hash, row, data);
                        removed_char_data[hash] = loaded_char_data[hash];
                        delete loaded_char_data[hash];
                        update_list_counts();
                    }
                    else {
                        console.log("Cannot add to favorites");
                    }
                }).catch(showResponse);
            }
        }
    });
}

function removeUndoRows(table) {
    $(table).find("tbody > tr").each(function() {
        if($(this).hasClass("undo-row")) {
            $(this).remove();
        }
    });
}

function populate_table(data, table_type, do_source_list=false) {
    $("#address-table").hide();
    $("tbody#address-table-body").empty();
    var char_data;
    var housing;
    var source_list = [];
    var orphaned = false;
    for (const [k, value] of Object.entries(data))
    {
        char_data = value.char_output;
        housing = value.housing_data;

        // Check against filters
        var passedFilters = false;
        if(filter_lists["city-filters"].length == 0 && filter_lists["suburb-filters"].length == 0 && filter_lists["neighborhood-filters"].length == 0)
            passedFilters = true;
        else {
            if(filter_lists["neighborhood-filters"].length > 0) {
                if(filter_lists["neighborhood-filters"].indexOf(housing["neighborhood"]) != -1)
                    passedFilters = true;
            }
            if(filter_lists["suburb-filters"].length > 0) {
                if(filter_lists["suburb-filters"].indexOf(housing["suburb"]) != -1)
                    passedFilters = true;
            }
            if(filter_lists["city-filters"].length > 0) {
                if(filter_lists["city-filters"].indexOf(housing["city"]) != -1)
                    passedFilters = true;
            }
        }

        if(!passedFilters)
            continue;

        if(k in orphaned_char_data)
            orphaned = true;
        else
            orphaned = false;
        if(!source_list.includes(housing["source"]))
            source_list.push(housing["source"]);
        if( char_data )
            $("tbody#address-table-body").append(create_table_row(k, char_data, housing, table_type, orphaned));
        else
            console.log("Missing characterization data for '" + housing["address"] + "'");
    }
    if(Object.keys(data).length == 0) {
        console.log("No data");
        $("tbody#address-table-body").append(`
            <tr>
                <td colspan="10"><p class="text-center">No data to display.</p></td>
            </tr>
        `);
    }
    if(do_source_list)
    {
        if($("#source-column > li").length == 0) {
            source_list.forEach(function(element) {
                const list_item = `
                    <li class="nav-item">
                        <a class="nav-link source-link" href="#">
                            <span class="badge badge-pill bg-primary text-light list-counter">0</span> ${element}
                        </a>
                    </li>
                `;
                $("#source-column").append(list_item);
            });

            $("a.source-link").click(function() {
                var source = $(this).text();
                clearListActive();
                $(this).addClass("active");
                $(this).append("<span class='current-tag'>(current)</span>");
                console.log("Switching to " + source);
                combined_source_data = {};
                for (const [k, value] of Object.entries(loaded_char_data))
                {
                    data_source = value.housing_data["source"];
                    if(data_source == source)
                        combined_source_data[k] = value;
                }
                populate_table(combined_source_data, TableType.TableAll);
                setupRowButtons();
            });
        }
    }
    $("#address-table").show();
}

function switch_to_all() {
    populate_table(loaded_char_data, TableType.TableAll, true);
    update_list_counts();
    setupRowButtons();
}

function switch_to_favorites() {
    // Get favorites data
    pywebview.api.get_favorites().then(function(response) {
        if(response) {
            populate_table(response, TableType.TableFavorites);
            update_list_counts();
            setupRowButtons();
        }
    }).catch(showResponse);
}
function switch_to_rejections() {
    // Get favorites data
    pywebview.api.get_rejections().then(function(response) {
        if(response) {
            populate_table(response, TableType.TableRejections);
            update_list_counts();
            setupRowButtons();
        }
    }).catch(showResponse);
}

window.addEventListener('pywebviewready', () => {
    pywebview.api.ready().then(function(response) {
        if(!response)
            postErrorAlert("Python API failed to initialize");

        // Add options filters
        pywebview.api.get_filter_choices("neighborhood").then(function(response) {
            for (var i = 0; i < response.length; i++) {
                $("#neighborhood-filters > select").append("<option>" + response[i] + "</option>")
            }
            sortSelectOptions($("#neighborhood-filters > select > option"));
        });
        pywebview.api.get_filter_choices("suburb").then(function(response) {
            for (var i = 0; i < response.length; i++) {
                $("#suburb-filters > select").append("<option>" + response[i] + "</option>")
            }
            sortSelectOptions($("#suburb-filters > select > option"));
        });
        pywebview.api.get_filter_choices("city").then(function(response) {
            for (var i = 0; i < response.length; i++) {
                $("#city-filters > select").append("<option>" + response[i] + "</option>")
            }
            sortSelectOptions($("#city-filters > select > option"));
        });
    }).catch(showResponse);
});

let filter_lists = {
    "neighborhood-filters": [],
    "suburb-filters": [],
    "city-filters": []
};

window.onload = function(e) {
    // Load the latest scrape data
    $("#master-error-alert").hide();
    $("#address-table").hide();
    $("#options-table").hide();

    $("#address-table > thead > tr > th.sortable-col > a").click(function() {
        let sort_column_idx = $("#address-table > thead > tr > th.sortable-col").toArray().indexOf($(this).parent()[0]);
        table = $(this).closest("table");
        removeUndoRows(table);
        items = $(table).find("tbody > tr").toArray();
        desc = $(table).prop("desc");
        is_money = $(this).parent().hasClass("sort-money");
        is_int = $(this).parent().hasClass("sort-float");
        // Sort remaining rows
        items.sort( function(a, b) {
            data_a = $($(a).find("td, th")[sort_column_idx]).text();
            data_b = $($(b).find("td, th")[sort_column_idx]).text();
            if(is_money) {
                data_a = parseFloat(data_a.replace('$', ''));
                data_b = parseFloat(data_b.replace('$', ''));
                if(data_a > data_b)
                    return 1;
                return -1;
            }
            else if(is_int) {
                data_a = parseFloat(data_a);
                data_b = parseFloat(data_b);
                if(isNaN(data_a))
                    return 1;
                if(isNaN(data_b))
                    return -1;
                if(data_a > data_b)
                    return 1;
                return -1;
            }
            return data_a.localeCompare(data_b);
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

    $("#all-data-link").click(function() {
        console.log("Switching to All Data");
        clearListActive();
        $(this).addClass("active");
        $(this).append("<span class='current-tag'>(current)</span>");
        switch_to_all();
    });
    $("#favorites-link").click(function() {
        console.log("Switching to Favorites");
        clearListActive();
        $(this).addClass("active");
        $(this).append("<span class='current-tag'>(current)</span>");
        switch_to_favorites();
    });
    $("#rejections-link").click(function() {
        console.log("Switching to Rejections");
        clearListActive();
        $(this).addClass("active");
        $(this).append("<span class='current-tag'>(current)</span>");
        switch_to_rejections();
    });

    $("#options-link").click(function() {
        console.log("Switching to Options");
        clearListActive();
        $(this).addClass("active");
        $(this).append("<span class='current-tag'>(current)</span>");
        $("#address-table").hide();
        $("#options-table").show();
    });

    $(".add-filter-btn").click(function() {
        var parentDiv = $(this).closest("div.filter-selectable");
        var selected = $(parentDiv).find(".custom-select").find(":selected").text();
        if(selected == "Choose...")
            return;
        var newFilterItem = $("<span class='filter-choice btn btn-danger'>" + selected + " X</span>");
        $(parentDiv).find("div.choices").append(newFilterItem);
        $(parentDiv).find(".custom-select > option:contains(" + selected + ")").remove()

        var filter_name = $(parentDiv).attr("id");
        filter_lists[filter_name].push(selected);

        $(newFilterItem).click(function() {
            var select = $(this).closest("div.filter-selectable").find(".custom-select");
            var selectedOption = $(select).find(":selected").text();
            $(select).append("<option>" + selected + "</option");
            $(this).remove();
            sortSelectOptions($(select).find("option"));

            filter_lists[filter_name].splice(filter_lists[filter_name].indexOf(selectedOption), 1);
        });
    });
};

function sortSelectOptions(select)
{
    var arr = select.map(function(_, o) { return { t: $(o).text(), v: o.value }; }).get();
    arr.sort(function(o1, o2) { return o1.t > o2.t ? 1 : o1.t < o2.t ? -1 : 0; });
    select.each(function(i, o) {
        o.value = arr[i].v;
        $(o).text(arr[i].t);
    });
}

function clearListActive()
{
    $(".sidebar-sticky > ul > li > a.nav-link").removeClass("active");
    $(".sidebar-sticky > ul > li > a.nav-link > span.current-tag").remove();
}

function update_list_counts()
{
    $("#all-data-link > .list-counter").text(Object.keys(loaded_char_data).length);
    pywebview.api.get_favorites_count().then(function(response) {
        $("#favorites-link > .list-counter").text(response);
    }).catch(showResponse);
    pywebview.api.get_rejections_count().then(function(response) {
        $("#rejections-link > .list-counter").text(response);
    }).catch(showResponse);
}

function create_table_row(hash, char_data, housing, table_type=TableType.TableAll, orphaned=false)
{
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
                train_elements += "<span class='train-green badge badge-pill'>&nbsp;&nbsp;</span>";
            else if( key == "Green Line (B)" )
                train_elements += "<span class='train-green badge badge-pill'>B</span>";
            else if( key == "Green Line (C)" )
                train_elements += "<span class='train-green badge badge-pill'>C</span>";
            else if( key == "Green Line (D)" )
                train_elements += "<span class='train-green badge badge-pill'>D</span>";
            else if( key == "Green Line (E)" )
                train_elements += "<span class='train-green badge badge-pill'>E</span>";
            else if( key == "Blue Line" )
                train_elements += "<span class='train-blue badge badge-pill'>&nbsp;&nbsp;</span>";
            else if( key == "Orange Line" )
                train_elements += "<span class='train-orange badge badge-pill'>&nbsp;&nbsp;</span>";
            else if( key == "Orange Line" )
                train_elements += "<span class='train-orange badge badge-pill'>&nbsp;&nbsp;</span>";
            else if( key == "Red Line (main)" )
                train_elements += "<span class='train-red badge badge-pill'>&nbsp;&nbsp;</span>";
            else if( key == "Red Line (Braintree)" )
                train_elements += "<span class='train-red badge badge-pill'>B</span>";
            else if( key == "Red Line (Ashmont)" )
                train_elements += "<span class='train-red badge badge-pill'>A</span>";
            else if( key == "Red Line (Mattapan)" )
                train_elements += "<span class='train-red badge badge-pill'>M</span>";
            else if( key == "Commuter Rail")
                train_elements += "<span class='train-commuter badge badge-pill'>&nbsp;&nbsp;</span>";
            else if( key == "Silver Line")
                train_elements += "<span class='train-silver badge badge-pill'>&nbsp;&nbsp;</span>";
            else
                console.log("Unknown train line: " + key)
        }
    }
    // Options
    var table_options = ``;
    var remove_text = "Remove";
    if(orphaned)
        remove_text = "DELETE";
    switch(table_type)
    {
    case TableType.TableFavorites:
        table_options = `
            <div class="options-btn-group btn-group btn-group-xs" role="group" aria-label="...">
                <button type="button" class="remove-button fav-button btn btn-danger btn-sm">${remove_text}</button>
            </div>
        `;
        break;
    case TableType.TableRejections:
        table_options = `
            <div class="options-btn-group btn-group btn-group-xs" role="group" aria-label="...">
                <button type="button" class="remove-button rej-button btn btn-danger btn-sm">${remove_text}</button>
            </div>
        `;
        break;
    case TableType.TableAll:
    default:
        table_options = `
            <div class="options-btn-group btn-group btn-group-xs" role="group" aria-label="...">
                <button type="button" class="fav-button btn btn-success btn-sm">Favorite</button>
                <button type="button" class="rej-button btn btn-danger btn-sm">Reject</button>
            </div>
        `;
        break;
    }
    if(orphaned)
        console.log("Orphan!");
    // Add row
    var table_row = `
        <tr hash="${hash}" class=${orphaned ? "table-danger" : ""}>
            <th scope="col" class="address-row">${housing["address"]}</th>
            <td>$${housing["rent"]}</td>
            <td>${(housing["beds"] ? housing["beds"] : "--")}</td>
            <td>${(housing["baths_str"] ? housing["baths_str"] : "--")}</td>
            <td>${(housing["sqft"] ? housing["sqft"] : "--")}</td>
            <td>${train_elements}</td>
            <td><span class="badge badge-pill badge-${color}">${(char_data["score"] * 100.0).toFixed(2)}</span></td>
            <td>${housing["source"]}</td>
            <td><a target="_new" href='${housing["link"]}'>Visit Page<a/></td>
            <td>${table_options}</td>
        </tr>
    `;
    return table_row;
}

function finished_json_load(char_json)
{
    loaded_char_data = char_json
    // Remove favorites and rejections
    pywebview.api.get_favorites().then(function(response) {
        if(response) {
            for (const [key, value] of Object.entries(response)) {
                if(key in loaded_char_data) {
                    removed_char_data[key] = loaded_char_data[key]
                    delete loaded_char_data[key];
                }
                else {
                    orphaned_char_data[key] = value;
                }
            }
        }
        switch_to_all();
    }).catch(showResponse);
    pywebview.api.get_rejections().then(function(response) {
        if(response) {
            for (const [key, value] of Object.entries(response)) {
                if(key in loaded_char_data) {
                    removed_char_data[key] = loaded_char_data[key]
                    delete loaded_char_data[key];
                }
                else {
                    orphaned_char_data[key] = value;
                }
            }
        }
        switch_to_all();
    }).catch(showResponse);
}

function load_json(char_avail=true) {
    if(char_avail) {
        $.getJSON(CHAR_FILE, finished_json_load);
    }
    else {
        postErrorAlert("There was no housing data! Run `pyagent.py -s` to scrape housing data.")
    }
}