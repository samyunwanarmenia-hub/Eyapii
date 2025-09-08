import { config, t } from './config.js';

export function initFan(app) {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(window.innerWidth < 600 ? 100 : 150, window.innerWidth < 600 ? 100 : 150);
    document.getElementById('fan-3d').appendChild(renderer.domElement);
    const geometry = new THREE.TorusGeometry(window.innerWidth < 600 ? 30 : 40, 10, 16, 100);
    const material = new THREE.MeshBasicMaterial({ color: app.WebApp?.themeParams?.accent_color || 0x00f0ff });
    const fan = new THREE.Mesh(geometry, material);
    scene.add(fan);
    camera.position.z = 100;
    const clock = new THREE.Clock();
    function animate() {
        requestAnimationFrame(animate);
        fan.rotation.z += app.userData.fan_speed * clock.getDelta() * 0.5;
        renderer.render(scene, camera);
    }
    animate();
}

export function initParticles(app) {
    particlesJS('particles-js', {
        particles: {
            number: { value: config.particles.number },
            color: { value: app.WebApp?.themeParams?.accent_text_color || '#ffd700' },
            shape: { type: 'circle' },
            size: { value: 3, random: true },
            move: { speed: 2, direction: 'random' }
        },
        interactivity: {
            events: {
                onhover: { enable: true, mode: 'repulse' },
                onclick: { enable: true, mode: 'push' }
            }
        }
    });
}

export function initTree(app) {
    const svg = d3.select("#tree-svg")
        .attr("width", config.tree.width)
        .attr("height", config.tree.height)
        .style("overflow", "visible");
    const g = svg.append("g");
    svg.call(d3.zoom().on("zoom", e => g.attr("transform", e.transform)));
    const treeLayout = d3.tree().size([config.tree.width - 100, config.tree.height - 100]);
    const root = d3.hierarchy(app.userData.tree[0]);
    treeLayout(root);
    g.selectAll(".link")
        .data(root.links())
        .enter().append("path")
        .attr("class", "link")
        .attr("d", d3.linkHorizontal().x(d => d.y + 50).y(d => d.x + 50))
        .attr("fill", "none")
        .attr("stroke", app.WebApp?.themeParams?.accent_color || "#00f0ff")
        .attr("stroke-width", 2)
        .style("opacity", 0)
        .transition().duration(1000).style("opacity", 1);
    g.selectAll(".node")
        .data(root.descendants())
        .enter().append("circle")
        .attr("cx", d => d.y + 50)
        .attr("cy", d => d.x + 50)
        .attr("r", d => d.data.name.includes(app.userData.name) ? 10 : 5)
        .attr("fill", d => {
            if (d.data.name.includes("Император") || d.data.name.includes("Emperor")) return "#ffd700";
            if (d.data.name.includes("Босс") || d.data.name.includes("Boss")) return "#00f0ff";
            return "#28a745";
        })
        .style("opacity", 0)
        .transition()
        .delay((d, i) => i * 100)
        .duration(1000)
        .style("opacity", 1)
        .on("click", (event, d) => app.WebApp?.showAlert(DOMPurify.sanitize(`${t('ru') === 'ru' ? 'Узел' : 'Node'}: ${d.data.name}`)));
    g.selectAll(".label")
        .data(root.descendants())
        .enter().append("text")
        .attr("x", d => d.y + 60)
        .attr("y", d => d.x + 55)
        .text(d => DOMPurify.sanitize(d.data.name))
        .attr("fill", app.WebApp?.themeParams?.text_color || "#fff")
        .style("font-size", window.innerWidth < 600 ? "12px" : "14px")
        .style("opacity", 0)
        .transition().duration(1000).style("opacity", 1);
}

export function initChart(app) {
    new Chart(document.getElementById('chart'), {
        type: 'line',
        data: {
            labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'].map(d => t(d)),
            datasets: [
                {
                    label: t('ru') === 'ru' ? 'Вложения USD 💰' : 'Investments USD 💰',
                    data: app.userData.investments,
                    borderColor: app.WebApp?.themeParams?.accent_color || '#00f0ff',
                    backgroundColor: app.WebApp?.themeParams?.accent_color ? `${app.WebApp.themeParams.accent_color}33` : 'rgba(0, 240, 255, 0.2)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: t('ru') === 'ru' ? 'Выплаты USD 💸' : 'Payouts USD 💸',
                    data: app.userData.payouts,
                    borderColor: app.WebApp?.themeParams?.secondary_bg_color || '#8b00ff',
                    backgroundColor: app.WebApp?.themeParams?.secondary_bg_color ? `${app.WebApp.themeParams.secondary_bg_color}33` : 'rgba(139, 0, 255, 0.2)',
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            animation: { duration: window.innerWidth < 600 ? 1000 : 2000, easing: 'easeInOutQuart' },
            plugins: {
                tooltip: {
                    backgroundColor: app.WebApp?.themeParams?.bg_color || '#1a1a2e',
                    titleColor: app.WebApp?.themeParams?.text_color || '#00f0ff',
                    bodyColor: app.WebApp?.themeParams?.text_color || '#fff'
                },
                legend: {
                    labels: {
                        color: app.WebApp?.themeParams?.text_color || '#fff',
                        font: { size: window.innerWidth < 600 ? 12 : 14, weight: 'bold', family: 'Roboto' }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: app.WebApp?.themeParams?.hint_color || 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: app.WebApp?.themeParams?.text_color || '#fff', font: { size: window.innerWidth < 600 ? 10 : 12 } }
                },
                x: {
                    grid: { color: app.WebApp?.themeParams?.hint_color || 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: app.WebApp?.themeParams?.text_color || '#fff', font: { size: window.innerWidth < 600 ? 10 : 12 } }
                }
            }
        }
    });
}