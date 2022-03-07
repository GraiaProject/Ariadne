
const admonition_titles = document.getElementsByClassName("admonition-title")
for (let i = 0; i < admonition_titles.length; i++) {
    let color = window.getComputedStyle(admonition_titles[i]).borderColor
    admonition_titles[i].style.color = color
}
const admonition_summaries = document.getElementsByTagName("SUMMARY")
for (let i = 0; i < admonition_summaries.length; i++) {
    let color = window.getComputedStyle(admonition_summaries[i]).borderColor
    admonition_summaries[i].style.color = color
}

function reload_color() {
    var p = localStorage.getItem("data-md-color-primary");
    if (p) {
        document.body.setAttribute('data-md-color-primary', p);
    }
    var a = localStorage.getItem("data-md-color-accent");
    if (a) {
        document.body.setAttribute('data-md-color-accent', a);
    }
}

window.addEventListener('change', reload_color, false);
window.addEventListener('load', reload_color, false);
