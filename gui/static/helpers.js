//HELPER FUNCTIONS
function byId(id){ return document.getElementById(id) }
String.prototype.toInt = function(){ return parseInt(this.replace(/,/g,''))}
HTMLElement.prototype.defaultCloneNode = HTMLElement.prototype.cloneNode
HTMLElement.prototype.cloneNode = function(attrs){
  const el = this.defaultCloneNode(this)
  Object.keys(attrs).forEach(k => el[k] = attrs[k])
  return el
}
HTMLElement.prototype.apply = function(transforms){
  for(key in transforms){
    const value = transforms[key]
    if(value instanceof HTMLElement) this.append(value)
    else if (key == 'style') for(prop of Object.keys(value)){ this[key][prop] = value[prop] }
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
async function toogle(button){
  try{
    button.children[0].style.visibility = 'collapse';
    button.children[1].style.visibility = 'visible';
    navigator.clipboard.writeText(button.getAttribute('data-value'))
    await sleep(1000)
  }
  catch(e){
    alert(button.getAttribute('data-value'))
  }
  finally{
    button.children[0].style.visibility = 'visible';
    button.children[1].style.visibility = 'collapse'
  }
}
function use(transformations){
  return { 
    fillWith: function(object, row = null){
      const tr = row ?? document.createElement("tr")
      for (id in transformations){
        const transforms = transformations[id](object)
        const td = document.createElement("td")
        td.apply(transforms)
        tr.append(td)
      }
      return tr
    }
  }
}
//END: COMMON FUNCTIONS & VARIABLES