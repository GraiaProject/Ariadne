
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

window.addEventListener('load', function () {
    var p = localStorage.getItem("data-md-color-primary");
    if (p) {
        document.body.setAttribute('data-md-color-primary', p);
    }
}, false);