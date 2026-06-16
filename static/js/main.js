// 冒险者公会 - 主脚本

// 自动消失的提示消息
$(document).ready(function() {
    setTimeout(function() {
        $('.alert-dismissible').fadeOut('slow');
    }, 5000);
});

// 表单验证增强
$(document).ready(function() {
    $('form').on('submit', function() {
        var btn = $(this).find('button[type="submit"]');
        if (btn.length) {
            btn.prop('disabled', true);
            // 如果不是确认类按钮，保留禁用状态
            if (!btn.text().includes('确认')) {
                setTimeout(function() { btn.prop('disabled', false); }, 3000);
            }
        }
    });
});

// 任务卡片点击跳转
$(document).ready(function() {
    $('.task-card').on('click', function() {
        var link = $(this).find('a.btn').attr('href');
        if (link) window.location.href = link;
    });
});
