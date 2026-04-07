/**
 * Sentix 前端交互脚本
 */

// 全局配置
const Sentix = {
    baseUrl: window.location.origin,
    csrfToken: null
};

// 工具函数
const Utils = {
    // 格式化日期
    formatDate: function(date) {
        if (!date) return '-';
        const d = new Date(date);
        return d.toLocaleDateString('zh-CN');
    },

    // 格式化时间
    formatTime: function(date) {
        if (!date) return '-';
        const d = new Date(date);
        return d.toLocaleString('zh-CN');
    },

    // 显示加载状态
    showLoading: function(element) {
        element.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">加载中...</span></div></div>';
    },

    // 隐藏加载状态
    hideLoading: function(element, content) {
        element.innerHTML = content;
    },

    // AJAX请求
    ajax: function(url, method, data, callback) {
        const xhr = new XMLHttpRequest();
        xhr.open(method, url, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onreadystatechange = function() {
            if (xhr.readyState === 4) {
                if (xhr.status === 200) {
                    callback(null, JSON.parse(xhr.responseText));
                } else {
                    callback(xhr.status, null);
                }
            }
        };
        xhr.send(JSON.stringify(data));
    },

    // 显示提示消息
    showToast: function(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('main.container').prepend(alertDiv);

        // 3秒后自动消失
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    }
};

// 文件上传处理
const FileUploader = {
    init: function() {
        const fileInput = document.querySelector('input[type="file"]');
        if (!fileInput) return;

        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            // 检查文件类型
            const allowedTypes = ['csv', 'json', 'xlsx'];
            const ext = file.name.split('.').pop().toLowerCase();
            if (!allowedTypes.includes(ext)) {
                Utils.showToast('不支持的文件格式', 'danger');
                fileInput.value = '';
                return;
            }

            // 检查文件大小 (16MB)
            if (file.size > 16 * 1024 * 1024) {
                Utils.showToast('文件大小不能超过16MB', 'danger');
                fileInput.value = '';
                return;
            }

            // 显示文件信息
            const fileInfo = document.createElement('div');
            fileInfo.className = 'mt-2 text-muted';
            fileInfo.innerHTML = `已选择: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
            fileInput.parentNode.appendChild(fileInfo);
        });
    }
};

// 表格处理
const TableHandler = {
    // 初始化表格排序
    initSorting: function(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;

        const headers = table.querySelectorAll('th[data-sortable]');
        headers.forEach(header => {
            header.addEventListener('click', function() {
                const column = this.dataset.column;
                const order = this.dataset.order || 'asc';
                TableHandler.sortTable(table, column, order);
                this.dataset.order = order === 'asc' ? 'desc' : 'asc';
            });
        });
    },

    // 排序表格
    sortTable: function(table, column, order) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));

        rows.sort((a, b) => {
            const aVal = a.querySelector(`td:nth-child(${column})`).textContent;
            const bVal = b.querySelector(`td:nth-child(${column})`).textContent;

            if (order === 'asc') {
                return aVal.localeCompare(bVal);
            } else {
                return bVal.localeCompare(aVal);
            }
        });

        rows.forEach(row => tbody.appendChild(row));
    }
};

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化文件上传
    FileUploader.init();

    // 自动关闭提示消息
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.remove();
        }, 5000);
    });

    // 初始化工具提示
    const tooltips = document.querySelectorAll('[title]');
    tooltips.forEach(el => {
        el.addEventListener('mouseenter', function() {
            this.dataset.originalTitle = this.title;
            this.title = '';
        });
        el.addEventListener('mouseleave', function() {
            this.title = this.dataset.originalTitle;
        });
    });
});

// 导出模块
window.Sentix = Sentix;
window.Utils = Utils;
window.FileUploader = FileUploader;
window.TableHandler = TableHandler;