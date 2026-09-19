let savedImageURL = ""; 

async function autoUploadImage(input) {
    if (!input.files || !input.files[0]) return;

    let file = input.files[0];
    let formData = new FormData();
    formData.append("file", file);

    document.getElementById("upload-status").innerText = "Rasm papkaga yuklanmoqda...";
    document.getElementById("preview-area").style.display = "block";

    try {
        let response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });

        if (response.ok) {
            let data = await response.json();
            savedImageURL = data.file_url; 

            document.getElementById("upload-status").innerText = "✅ Rasm yuklandi!";
            document.getElementById("img-preview").src = savedImageURL;
        } else {
            document.getElementById("upload-status").innerText = "❌ Yuklashda xatolik yuz berdi.";
        }
    } catch (error) {
        console.error("Xatolik:", error);
        document.getElementById("upload-status").innerText = "❌ Server bilan aloqa yo'q.";
    }
}
