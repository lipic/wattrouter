function _cacheScript(e,t,a){var n=new XMLHttpRequest;n.onreadystatechange=function(){4==n.readyState&&200==n.status&&localStorage.setItem(e,JSON.stringify({content:n.responseText,version:t}))},n.open("GET",a,!0),n.send()}function _loadScript(e,t,a,n){var r=document.createElement("script");r.type="application/javascript",r.readyState?r.onreadystatechange=function(){"loaded"!=r.readyState&&"complete"!=r.readyState||(r.onreadystatechange=null,_cacheScript(t,a,e),n&&n())}:r.onload=function(){_cacheScript(t,a,e),n&&n()},r.setAttribute("src",e),document.getElementsByTagName("head")[0].appendChild(r)}function _injectScript(e,t,a,n,r){var c=JSON.parse(e);if(c.version!=n)return localStorage.removeItem(a),void _loadScript(t,a,n,r);var i=document.createElement("script");i.defer=!0,i.type="application/javascript";var p=document.createTextNode(c.content);i.appendChild(p),document.getElementsByTagName("head")[0].appendChild(i),r&&r()}function requireScript(e,t,a,n){try{var r;null==(r=localStorage.getItem(e))?_loadScript(a,e,t,n):_injectScript(r,a,e,t,n)}catch(c){}}