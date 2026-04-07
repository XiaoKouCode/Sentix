/**
 * ECharts图表配置脚本
 */

// 图表主题配置
const ChartTheme = {
    colors: ['#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6610f2', '#6c757d'],
    backgroundColor: 'transparent',
    textStyle: {
        fontFamily: 'Microsoft YaHei, PingFang SC, Arial'
    }
};

// 情感分布饼图
function createSentimentPieChart(containerId, data) {
    const chart = echarts.init(document.getElementById(containerId));

    const option = {
        title: {
            text: '情感分布',
            left: 'center',
            textStyle: ChartTheme.textStyle
        },
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
        },
        legend: {
            orient: 'vertical',
            left: 'left',
            data: ['积极', '消极', '中性']
        },
        series: [{
            name: '情感分布',
            type: 'pie',
            radius: ['40%', '70%'],
            avoidLabelOverlap: false,
            itemStyle: {
                borderRadius: 10,
                borderColor: '#fff',
                borderWidth: 2
            },
            label: {
                show: true,
                formatter: '{b}: {d}%'
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 16,
                    fontWeight: 'bold'
                }
            },
            data: [
                { value: data.positive, name: '积极', itemStyle: { color: '#28a745' } },
                { value: data.negative, name: '消极', itemStyle: { color: '#dc3545' } },
                { value: data.neutral, name: '中性', itemStyle: { color: '#ffc107' } }
            ]
        }]
    };

    chart.setOption(option);
    return chart;
}

// 情感柱状图
function createSentimentBarChart(containerId, data) {
    const chart = echarts.init(document.getElementById(containerId));

    const option = {
        title: {
            text: '情感数量统计',
            left: 'center',
            textStyle: ChartTheme.textStyle
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: ['积极', '消极', '中性']
        },
        yAxis: {
            type: 'value'
        },
        series: [{
            data: [
                { value: data.positive, itemStyle: { color: '#28a745' } },
                { value: data.negative, itemStyle: { color: '#dc3545' } },
                { value: data.neutral, itemStyle: { color: '#ffc107' } }
            ],
            type: 'bar',
            barWidth: '40%',
            label: {
                show: true,
                position: 'top'
            }
        }]
    };

    chart.setOption(option);
    return chart;
}

// 关键词柱状图
function createKeywordChart(containerId, keywords) {
    const chart = echarts.init(document.getElementById(containerId));

    const words = keywords.map(k => k[0]);
    const counts = keywords.map(k => k[1]);

    const option = {
        title: {
            text: '高频关键词',
            left: 'center',
            textStyle: ChartTheme.textStyle
        },
        tooltip: {
            trigger: 'axis'
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: words,
            axisLabel: {
                rotate: 45,
                interval: 0
            }
        },
        yAxis: {
            type: 'value'
        },
        series: [{
            data: counts,
            type: 'bar',
            itemStyle: {
                color: '#17a2b8'
            },
            label: {
                show: true,
                position: 'top'
            }
        }]
    };

    chart.setOption(option);
    return chart;
}

// 商品对比图
function createProductCompareChart(containerId, products) {
    const chart = echarts.init(document.getElementById(containerId));

    const names = products.map(p => p.name || '未知商品');

    const option = {
        title: {
            text: '各商品情感分布',
            left: 'center',
            textStyle: ChartTheme.textStyle
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            }
        },
        legend: {
            data: ['积极', '消极', '中性'],
            top: 30
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: names
        },
        yAxis: {
            type: 'value'
        },
        series: [
            {
                name: '积极',
                type: 'bar',
                stack: 'total',
                data: products.map(p => p.positive),
                itemStyle: { color: '#28a745' }
            },
            {
                name: '消极',
                type: 'bar',
                stack: 'total',
                data: products.map(p => p.negative),
                itemStyle: { color: '#dc3545' }
            },
            {
                name: '中性',
                type: 'bar',
                stack: 'total',
                data: products.map(p => p.neutral),
                itemStyle: { color: '#ffc107' }
            }
        ]
    };

    chart.setOption(option);
    return chart;
}

// 情感趋势图
function createTrendChart(containerId, trendData) {
    const chart = echarts.init(document.getElementById(containerId));

    const dates = trendData.map(d => d.date);
    const scores = trendData.map(d => d.score);

    const option = {
        title: {
            text: '情感趋势变化',
            left: 'center',
            textStyle: ChartTheme.textStyle
        },
        tooltip: {
            trigger: 'axis'
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: dates,
            boundaryGap: false
        },
        yAxis: {
            type: 'value',
            min: 0,
            max: 1
        },
        series: [{
            data: scores,
            type: 'line',
            smooth: true,
            itemStyle: {
                color: '#667eea'
            },
            areaStyle: {
                color: {
                    type: 'linear',
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                        { offset: 0, color: 'rgba(102, 126, 234, 0.5)' },
                        { offset: 1, color: 'rgba(102, 126, 234, 0.1)' }
                    ]
                }
            }
        }]
    };

    chart.setOption(option);
    return chart;
}

// 窗口大小变化时重新调整图表
window.addEventListener('resize', function() {
    echarts.instances.forEach(chart => {
        chart.resize();
    });
});

// 导出函数
window.ChartTheme = ChartTheme;
window.createSentimentPieChart = createSentimentPieChart;
window.createSentimentBarChart = createSentimentBarChart;
window.createKeywordChart = createKeywordChart;
window.createProductCompareChart = createProductCompareChart;
window.createTrendChart = createTrendChart;