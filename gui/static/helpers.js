//HELPER FUNCTIONS
function byId(id){ return document.getElementById(id) }
String.prototype.toInt = function(){ return parseInt(this.replace(/,/g,''))}
String.prototype.toBool = function(if_false = 0){ return this && /^true$/i.test(this) ? 1 : if_false}
Number.prototype.intcomma = function(){ return parseInt(this).toLocaleString() }
HTMLElement.prototype.defaultCloneNode = HTMLElement.prototype.cloneNode
HTMLElement.prototype.cloneNode = function(attrs){
  const el = this.defaultCloneNode(this)
  Object.keys(attrs).forEach(k => el[k] = attrs[k])
  return el
}
HTMLElement.prototype.render = function(transforms){
  for(key in transforms){
    const value = transforms[key]
    if(value instanceof HTMLElement) this.append(value)
    else if (key === 'style') for(prop of Object.keys(value)){ this[key][prop] = value[prop] }
    else this[key] = value
  }
}
//END: HELPER FUNCTIONS
//-------------------------------------------------------------------------------------------------------------------------
//COMMON FUNCTIONS & VARIABLES
const red = 'rgba(248,81,73,0.15)'
const green = 'rgba(46,160,67,0.15)'
function sleep(ms){
  return new Promise(res => setTimeout(res, ms));
}
function adjustTZ(datetime){
  datetime = new Date(datetime).getTime() - new Date(datetime).getTimezoneOffset()*60000
  return new Date(datetime)
}
async function toggle(button){
  try{
    button.children[0].style.visibility = 'hidden';
    button.children[1].style.visibility = 'visible';
    navigator.clipboard.writeText(button.getAttribute('data-value'))
    await sleep(1000)
  }
  catch(e){
    alert(button.getAttribute('data-value'))
  }
  finally{
    button.children[0].style.visibility = 'visible';
    button.children[1].style.visibility = 'hidden'
  }
}
function use(template){
  return { 
    render: function(object, id='id', row = null){
      const tr = row ?? document.createElement("tr")
      tr.objId = object[id]
      for (key in template){
        const transforms = template[key](object)
        const td = document.createElement("td")
        td.setAttribute('name', key)
        td.render(transforms)
        tr.append(td)
      }
      return tr
    }
  }
}
function showBannerMsg(h1Msg, result, generic=false, id="bannerMsg"){
  if(!generic) h1Msg = `${h1Msg} updated to:`
  document.getElementById('content').insertAdjacentHTML("beforebegin", `<div style="top:5px;padding:10px;" id="${id}" class="message w3-panel w3-orange w3-display-container"><span onclick="this.parentElement.style.display='none'" class="w3-button w3-hover-red w3-display-topright">X</span><h1 style="word-wrap: break-word">${h1Msg} ${result}</h1></div>`);
  window.scrollTo(0, 0);
}
function flash(element, response){
  if (response != element.value) {
      element.value = response
      return
  }
  var rgb = window.getComputedStyle(element).backgroundColor;
  rgb = rgb.substring(4, rgb.length-1).replace(/ /g, '').split(',');
  var r = rgb[0], g = rgb[1], bOrigin = rgb[2], b = bOrigin;
  var add = false;
  var complete = false;
  const increment = 15;
  var flashOn = setInterval(() => {
      if(add){
          if(b < 255 && (b+increment) <= 255){
              b += increment;
          }else{
              add = false;
              complete = true;
          }
      }else{
          if(complete == true && b < bOrigin){
              b = bOrigin;
              clearInterval(flashOn);
          }
          else if(b > 0 && (b-increment) >= 0){
              b -= increment;
          }else{
              add = true;
          }
      }
      element.style.backgroundColor = 'RGB('+r+','+g+','+b+')';
      if(b == bOrigin) element.style.removeProperty("background-color");
  }, 50);
}
function formatDate(start, end = new Date().getTime() + new Date().getTimezoneOffset()*60000){
  if (end == null) return '---'
  end = new Date(end)
  if (start == null) return '---'
  difference = (end - new Date(start))/1000
  if (difference > 0) {
    if (difference < 60) {
      if (Math.floor(difference) == 1){
          return `a second ago`;
      }else{
          return `${Math.floor(difference)} seconds ago`;
      }
    } else if (difference < 3600) {
        if (Math.floor(difference / 60) == 1){
            return `a minute ago`;
        }else{
            return `${Math.floor(difference / 60)} minutes ago`;
        }
    } else if (difference < 86400) {
        if (Math.floor(difference / 3600) == 1){
            return `an hour ago`;
        }else{
            return `${Math.floor(difference / 3600)} hours ago`;
        }
    } else if (difference < 2620800) {
        if (Math.floor(difference / 86400) == 1){
            return `a day ago`;
        }else{
            return `${Math.floor(difference / 86400)} days ago`;
        }
    } else if (difference < 31449600) {
        if (Math.floor(difference / 2620800) == 1){
            return `a month ago`;
        }else{
            return `${Math.floor(difference / 2620800)} months ago`;
        }
    } else {
        if (Math.floor(difference / 31449600) == 1){
            return `a year ago`;
        }else{
            return `${Math.floor(difference / 31449600)} years ago`;
        }
    }   
  } else if (difference < 0) {
    if (-difference < 60) {
      if (Math.floor(-difference) == 1){
          return `in a second`;
      }else{
          return `in ${Math.floor(-difference)} seconds`;
      }
    } else if (-difference < 3600) {
        if (Math.floor(-difference / 60) == 1){
            return `in a minute`;
        }else{
            return `in ${Math.floor(-difference / 60)} minutes`;
        }
    } else if (-difference < 86400) {
        if (Math.floor(-difference / 3600) == 1){
            return `in an hour`;
        }else{
            return `in ${Math.floor(-difference / 3600)} hours`;
        }
    } else if (-difference < 2620800) {
        if (Math.floor(-difference / 86400) == 1){
            return `in a day`;
        }else{
            return `in ${Math.floor(-difference / 86400)} days`;
        }
    } else if (-difference < 31449600) {
        if (Math.floor(-difference / 2620800) == 1){
            return `in a month`;
        }else{
            return `in ${Math.floor(-difference / 2620800)} months`;
        }
    } else {
        if (Math.floor(-difference / 31449600) == 1){
            return `in a year`;
        }else{
            return `in ${Math.floor(-difference / 31449600)} years`;
        }
    } 
  } else { return 'Just now' }
}
//END: COMMON FUNCTIONS & VARIABLES