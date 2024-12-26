document.addEventListener("DOMContentLoaded", () => {
    const likeButton = document.getElementById("like-button");
    const notification = document.createElement("div"); // Bildirim elemanı oluştur
    document.body.appendChild(notification); // Bildirimi gövdeye ekle

    let isLiked = false; // Kullanıcının beğenip beğenmediğini takip eder

    // HTML'den resim yollarını al
    const emptyHeart = likeButton.getAttribute("data-heart"); // Flask'ın static klasöründeki boş kalp
    const filledHeart = likeButton.getAttribute("data-heart-filled"); // Dolu kalp

        // Bildirim stilini ayarla
    notification.style.position = "fixed";
    notification.style.top = "5px";
    notification.style.left = "50%";
    notification.style.transform = "translateX(-50%)"; // Yatay olarak tam merkezleme
    notification.style.padding = "10px 20px";
    notification.style.backgroundColor = "#144635";
    notification.style.color = "#f7e1af";
    notification.style.borderRadius = "5px";
    notification.style.fontSize = "16px";
    notification.style.display = "none"; // Başlangıçta görünmez

    const showNotification = (message) => {
        notification.textContent = message;
        notification.style.display = "block";
        setTimeout(() => {
            notification.style.display = "none";
        }, 2000); // 2 saniye sonra gizle
    };

    likeButton.addEventListener("click", (event) => {
        event.preventDefault(); // Form gönderimini engeller

        if (isLiked) {
            likeButton.src = emptyHeart; // Boş kalp simgesi
            showNotification("You unliked this recipe");
        } else {
            likeButton.src = filledHeart; // Dolu kalp simgesi
            showNotification("You liked this recipe");
        }

        isLiked = !isLiked; // Durumu tersine çevir
    });
});
