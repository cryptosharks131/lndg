function sortTable(n, type, tableName, skip=0, link=false) {
    var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
    var upArrow = " ▲", downArrow = " ▼";
    table = document.getElementById(tableName);
    header = table.rows[0+skip].getElementsByTagName("TH")[n];

    switching = true;
    dir = "asc";
    while (switching) {
        switching = false;
        rows = table.rows;
        for (i=1+skip; i<(rows.length-1); i++) {
            shouldSwitch = false;
            if (link == true) {
                x = rows[i].getElementsByTagName("A")[n];
                y = rows[i+1].getElementsByTagName("A")[n];                
            } else {
                x = rows[i].getElementsByTagName("TD")[n];
                y = rows[i+1].getElementsByTagName("TD")[n];
            }
            if (dir == "asc") {
                if (type == "String" && x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()
                    || type == "int" && parseInt(x.innerHTML.replace(/,/g, '')) > parseInt(y.innerHTML.replace(/,/g, ''))
                    || type != "String" && type != "int" && Number(x.innerHTML.toLowerCase().split(type)[0].replace(/,/g, '')) > Number(y.innerHTML.toLowerCase().split(type)[0].replace(/,/g, ''))) 
                {
                    shouldSwitch = true;
                    break;
                }
            } else if (dir == "desc") {
                if (type == "String" && x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()
                    || type == "int" && parseInt(x.innerHTML.replace(/,/g, '')) < parseInt(y.innerHTML.replace(/,/g, ''))
                    || type != "String" && type != "int" && Number(x.innerHTML.toLowerCase().split(type)[0].replace(/,/g, '')) < Number(y.innerHTML.toLowerCase().split(type)[0].replace(/,/g, ''))) 
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