async function GET(url, {method = 'GET', data = null}){
    return call({url, method, data})
}

async function POST(url, {method = 'POST', body}){
    return call({url: url + '/', method, body})
}

async function PUT(url, {method = 'PUT', body}){
    return call({url: url + '/', method, body})
}

async function PATCH(url, {method = 'PATCH', body}){
    return call({url: url + '/', method, body})
}

async function DELETE(url, {method = 'DELETE'}){
    return call({url: url + '/', method})
}

async function call({url, method, data, body, headers = {'Content-Type':'application/json'}}){
    if(method != 'GET') headers['X-CSRFToken'] = document.getElementById('api').dataset.token
    const result = await fetch(`api/${url}${data ? '?': ''}${new URLSearchParams(data).toString()}`, {method, body: JSON.stringify(body), headers})
    return result.json()
}

class Sync{
    static PUT(url, {method = 'PUT', body}, callback){
        call({url: url + '/', method, body}).then(res => callback(res))
    }
}

function showBannerMsg(h1Msg, result){
    document.getElementById('content').insertAdjacentHTML("beforebegin", `<div style="top:5px" class="message w3-panel w3-orange w3-display-container"><span onclick="this.parentElement.style.display='none'" class="w3-button w3-hover-red w3-display-topright">X</span><h1 style="word-wrap: break-word">${h1Msg} updated to: ${result}</h1></div>`);
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
    if (difference < 0) return 'Just now'
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
}