// CSMC 饰品交易平台 - 前端交互

document.addEventListener("DOMContentLoaded", function () {
  // 移动端导航切换
  const navToggle = document.getElementById("navToggle");
  const mobileNav = document.getElementById("mobileNav");
  if (navToggle && mobileNav) {
    navToggle.addEventListener("click", function () {
      mobileNav.classList.toggle("open");
    });
  }

  // 自动关闭消息提示
  document.querySelectorAll(".flash").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity .4s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 400);
    }, 4000);
  });

  // 复制 QQ 号
  document.querySelectorAll("[data-copy-qq]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const qq = btn.getAttribute("data-copy-qq");
      copyText(qq, btn);
    });
  });

  // 磨损输入格式化（保留6位小数）
  document.querySelectorAll("input[name='wear']").forEach(function (input) {
    input.addEventListener("blur", function () {
      const val = parseFloat(input.value);
      if (!isNaN(val)) {
        input.value = val.toFixed(6);
      }
    });
  });
});

// 复制文本到剪贴板
function copyText(text, btn) {
  const fallback = function () {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
  };
  const done = function () {
    if (btn) {
      const orig = btn.textContent;
      btn.textContent = "已复制";
      btn.classList.add("copied");
      setTimeout(function () {
        btn.textContent = orig;
        btn.classList.remove("copied");
      }, 1500);
    }
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(function () {
      fallback();
      done();
    });
  } else {
    fallback();
    done();
  }
}

// 发起 QQ 临时会话
function openQQChat(qq) {
  window.open("https://wpa.qq.com/msgrd?v=3&uin=" + encodeURIComponent(qq) + "&site=qq&menu=yes", "_blank");
}
