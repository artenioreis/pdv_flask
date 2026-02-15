// static/js/dashboard.js
document.addEventListener('DOMContentLoaded', function() {
    // Função para buscar dados e renderizar o gráfico de Top Produtos
    function fetchTopProducts() {
        fetch('/reports/top_products') // Novo endpoint para top produtos
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erro ao buscar dados de top produtos.');
                }
                return response.json();
            })
            .then(data => {
                const ctx = document.getElementById('topProductsChart').getContext('2d');
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.map(item => item.name),
                        datasets: [{
                            label: 'Quantidade Vendida',
                            data: data.map(item => item.quantity),
                            backgroundColor: [
                                'rgba(0, 123, 255, 0.7)', // primary-color
                                'rgba(40, 167, 69, 0.7)',  // secondary-color
                                'rgba(23, 162, 184, 0.7)', // info-color
                                'rgba(255, 193, 7, 0.7)',  // warning-color
                                'rgba(220, 53, 69, 0.7)'   // danger-color
                            ],
                            borderColor: [
                                'rgba(0, 123, 255, 1)',
                                'rgba(40, 167, 69, 1)',
                                'rgba(23, 162, 184, 1)',
                                'rgba(255, 193, 7, 1)',
                                'rgba(220, 53, 69, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Quantidade'
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Produto'
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false // Não precisa de legenda para um único dataset
                            }
                        }
                    }
                });
            })
            .catch(error => {
                console.error('Erro ao carregar gráfico de top produtos:', error);
                document.getElementById('topProductsChart').parentElement.innerHTML = '<p class="text-danger text-center">Não foi possível carregar o gráfico de produtos mais vendidos.</p>';
            });
    }

    // Função para buscar dados e renderizar o gráfico de Vendas Diárias
    function fetchDailySales() {
        fetch('/reports/daily_sales') // Novo endpoint para vendas diárias
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erro ao buscar dados de vendas diárias.');
                }
                return response.json();
            })
            .then(data => {
                const ctx = document.getElementById('dailySalesChart').getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.map(item => item.date), // Datas formatadas
                        datasets: [{
                            label: 'Receita Diária (R$)',
                            data: data.map(item => item.revenue),
                            backgroundColor: 'rgba(0, 123, 255, 0.2)', // primary-color com transparência
                            borderColor: 'rgba(0, 123, 255, 1)', // primary-color
                            borderWidth: 2,
                            fill: true,
                            tension: 0.3 // Suaviza a linha
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Receita (R$)'
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Data'
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            }
                        }
                    }
                });
            })
            .catch(error => {
                console.error('Erro ao carregar gráfico de vendas diárias:', error);
                document.getElementById('dailySalesChart').parentElement.innerHTML = '<p class="text-danger text-center">Não foi possível carregar o gráfico de vendas diárias.</p>';
            });
    }

    // Chama as funções para carregar os gráficos quando a página é carregada
    fetchTopProducts();
    fetchDailySales();
});
