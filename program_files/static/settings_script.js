const force_h264 = window.config.force_h264;
let dropdownVisibility = false;

function gpu_dropdown(){
    const codec = document.getElementById("codec")

    console.log(codec.value)
    if (force_h264){
        dropdownVisibility = true;
        const codec_selection = document.getElementById("codec_selection");
        codec_selection.style = "display: block";
    }
    codec.addEventListener("change", toggleDropdown);
}

function toggleDropdown(){
    if (dropdownVisibility == true){
        const codec_selection = document.getElementById("codec_selection");
        codec_selection.style = "display: none";
        dropdownVisibility = false;
    } else {
        const codec_selection = document.getElementById("codec_selection");
        codec_selection.style = "display: block";
        dropdownVisibility = true;
    }
}

gpu_dropdown();