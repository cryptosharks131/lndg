function getCookie(cname) {
    let name = cname + "=";
    let ca = document.cookie.split(';');
    for(let i = 0; i < ca.length; i++) {
      let c = ca[i];
      while (c.charAt(0) == ' ') {
        c = c.substring(1);
      }
      if (c.indexOf(name) == 0) {
        return c.substring(name.length, c.length);
      }
    }
    return "";
  }

function darkMode() {
    let darkmode = getCookie("darkmode");
    if (darkmode != "") {
        if (darkmode == "true") {
          document.cookie = "darkmode=false";
        } else {
          document.cookie = "darkmode=true";
        }
    } else {
        document.cookie = "darkmode=true"; 
    }
    var element = document.body;
    element.classList.toggle("dark-mode");
    element.classList.toggle("dark-mode-table1");
    element.classList.toggle("dark-mode-table2");
}

function checkDarkMode() {
    let darkmode = getCookie("darkmode");
    if (darkmode == "true") {
        var element = document.body;
        element.classList.toggle("dark-mode");
        element.classList.toggle("dark-mode-table1");
        element.classList.toggle("dark-mode-table2");
    }
}