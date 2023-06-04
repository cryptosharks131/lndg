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
function applyTheme(){
  if(getCookie("darkmode") == "true"){
    toggleTheme();
  }
}

function toggleTheme() {
  var element = document.body;
  element.classList.toggle("dark-mode")
  document.cookie = `darkmode=${element.classList.contains("dark-mode")};max-age=34560000`
}