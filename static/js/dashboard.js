// static/js/dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    // Função para buscar dados e renderizar o gráfico de Top Produtos (COLUNAS)
    function fetchTopProducts() {
        fetch('/reports/top_products')
            .then(response => {
                if (!response.ok) throw new Error('Erro ao buscar dados de top produtos.');
                return response.json();
            })
            .then(data => {
                const ctx = document.getElementById('topProductsChart').getContext('2d');
                new Chart(ctx, {
                    type: 'bar', // Gráfico de Colunas/Barras
                    data: {
                        labels: data.map(item => item.name),
                        datasets: [{
                            label: 'Quantidade Vendida',
                            data: data.map(item => item.quantity),
                            backgroundColor: 'rgba(0, 123, 255, 0.7)',
                            borderColor: 'rgba(0, 123, 255, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: { beginAtZero: true }
                        },
                        plugins: { legend: { display: false } }
                    }
                });
            })
            .catch(error => {
                console.error(error);
                document.getElementById('topProductsChart').parentElement.innerHTML = '<p class="text-danger text-center">Dados de venda insuficientes.</p>';
            });
    }

    // Função para buscar dados e renderizar o gráfico de Vendas Diárias (LINHA)
    function fetchDailySales() {
        fetch('/reports/daily_sales')
            .then(response => {
                if (!response.ok) throw new Error('Erro ao buscar dados de vendas diárias.');
                return response.json();
            })
            .then(data => {
                const ctx = document.getElementById('dailySalesChart').getContext('2d');
                new Chart(ctx, {
                    type: 'line', // Gráfico de Linha
                    data: {
                        labels: data.map(item => item.date),
                        datasets: [{
                            label: 'Receita Diária (R$)',
                            data: data.map(item => item.revenue),
                            backgroundColor: 'rgba(40, 167, 69, 0.2)',
                            borderColor: 'rgba(40, 167, 69, 1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.3
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: { beginAtZero: true }
                        },
                        plugins: { legend: { display: false } }
                    }
                });
            })
            .catch(error => {
                console.error(error);
                document.getElementById('dailySalesChart').parentElement.innerHTML = '<p class="text-danger text-center">Sem dados para os últimos 7 dias.</p>';
            });
    }

    fetchTopProducts();
    fetchDailySales();
});