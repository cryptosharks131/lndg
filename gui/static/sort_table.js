function sortTable(header, n, type, skip=0, tag="td") {
    var switching, i, curr_row, next_row, shouldSwitch, dir, switchcount = 0;
    var upArrow = " ▲", downArrow = " ▼";
    var table = header.parentElement.parentElement.parentElement; //th.tr.tbody.table
    var rows = table.rows;

    switching = true;
    dir = "asc";
    while (switching) {
        switching = false;
        for (i=1+skip; i<(rows.length-1); i++) {
            shouldSwitch = false;
            curr_row = rows[i].children[n]
            next_row = rows[i+1].children[n]
            if(tag !== "td"){
                curr_row = curr_row.getElementsByTagName(tag)[0];
                next_row = next_row.getElementsByTagName(tag)[0];
            }   
            if (dir == "asc") {
                if (type == "String" && curr_row.innerHTML.toLowerCase() > next_row.innerHTML.toLowerCase()
                    || type == "int" && parseFloat(curr_row.innerHTML.replace(/,/g, '')) > parseFloat(next_row.innerHTML.replace(/,/g, ''))
                    || type != "String" && type != "int" && Number(curr_row.innerHTML.toLowerCase().split(type)[0].replace(/,/g, '')) > Number(next_row.innerHTML.toLowerCase().split(type)[0].replace(/,/g, ''))) 
                {
                    shouldSwitch = true;
                    break;
                }
            } else if (dir == "desc") {
                if (type == "String" && curr_row.innerHTML.toLowerCase() < next_row.innerHTML.toLowerCase()
                    || type == "int" && parseFloat(curr_row.innerHTML.replace(/,/g, '')) < parseFloat(next_row.innerHTML.replace(/,/g, ''))
                    || type != "String" && type != "int" && Number(curr_row.innerHTML.toLowerCase().split(type)[0].replace(/,/g, '')) < Number(next_row.innerHTML.toLowerCase().split(type)[0].replace(/,/g, ''))) 
                {
                    shouldSwitch = true;
                    break;
                }
            }
        }
        if (shouldSwitch) {
            rows[i].parentNode.insertBefore(rows[i+1], rows[i]);
            switching = true;
            switchcount ++;
        } else {
            if (switchcount == 0 && dir == "asc") {
                dir = "desc";
                switching = true;
            }
        }
    }

    if (switchcount > 0) {
        for (i=0; i<table.rows[0+skip].cells.length; i++) {
            currHeader = rows[0+skip].getElementsByTagName("TH")[i].innerHTML;
            if (currHeader.substring(currHeader.length-1) == "▲" || currHeader.substring(currHeader.length-1) == "▼") {
                rows[0+skip].getElementsByTagName("TH")[i].innerHTML = currHeader.substring(0, currHeader.length-2);
            }
        }
        if (dir == "asc") header.innerHTML += upArrow;
        else header.innerHTML += downArrow;
    }
}