const APPROACHES = {
  1: {
    title: 'Approach 1 – BPE / PMI co-occurrence',
    description: 'Tokenizes the clinical text and builds a PMI-style correlation graph from nearby concepts.'
  },
  2: {
    title: 'Approach 2 – POS tagging graph',
    description: 'Uses grammatical patterns and a medical vocabulary to construct a syntactic relationship graph.'
  },
  3: {
    title: 'Approach 3 – Rule-based clinical graph',
    description: 'Extracts medical terms, negations, exams and measurements to connect them to the patient.'
  },
  4: {
    title: 'Approach 4 – Controlled gazetteer graph',
    description: 'Builds a strictly vocabulary-driven graph from clinical concepts and known measurement rules.'
  }
};

const DEFAULT_TEXT = 'A 56-year-old woman presented with abdominal pain and nausea. CT scan showed a pancreatic cyst. Labs: CA 19-9 12,476.5 ng/mL and 6 cm mass. The patient had no fever and no constipation. Follow-up imaging revealed a 3 cm lesion in the pancreas.';
const API_BASE = window.NLP_GRAPH_API_URL || 'http://localhost:8001';

let selectedApproach = 1;
let network;

function init() {
  renderApproachTabs();
  bindEvents();
  applyApproach(selectedApproach);
}

function renderApproachTabs() {
  const tabs = document.getElementById('solution-tabs');
  tabs.replaceChildren();

  Object.entries(APPROACHES).forEach(([id, approach]) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'solution-tab';
    if (Number(id) === selectedApproach) {
      button.classList.add('active');
    }
    button.textContent = approach.title;
    button.dataset.id = id;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-selected', String(Number(id) === selectedApproach));

    button.addEventListener('click', () => {
      selectedApproach = Number(id);
      renderApproachTabs();
      applyApproach(selectedApproach);
    });

    tabs.appendChild(button);
  });
}

function bindEvents() {
  document.getElementById('build-button').addEventListener('click', () => {
    applyApproach(selectedApproach);
  });

  document.getElementById('sample-button').addEventListener('click', () => {
    document.getElementById('input-text').value = DEFAULT_TEXT;
    applyApproach(selectedApproach);
  });
}

async function applyApproach(id) {
  const text = document.getElementById('input-text').value || DEFAULT_TEXT;
  const method = APPROACHES[id];

  if (!method) {
    return;
  }

  document.getElementById('summary').innerHTML = '<strong>Loading...</strong>';

  try {
    const response = await fetch(`${API_BASE}/api/graph?solution=${id}&text=${encodeURIComponent(text)}`);
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    const payload = await response.json();
    if (payload.error) {
      throw new Error(payload.error);
    }

    renderGraph(payload.nodes || [], payload.edges || []);
    document.getElementById('summary').innerHTML = `
      <strong>Method:</strong> ${method.title}<br>
      <strong>Nodes:</strong> ${payload.summary?.node_count ?? 0}<br>
      <strong>Edges:</strong> ${payload.summary?.edge_count ?? 0}<br>
      <strong>Input length:</strong> ${payload.summary?.input_length ?? text.length} chars<br>
      <small>${method.description}</small>
    `;
  } catch (error) {
    document.getElementById('summary').innerHTML = `
      <strong>Error:</strong> ${error.message}<br>
      <small>Check that the Python API is running at ${API_BASE}.</small>
    `;
    renderGraph([], []);
  }
}

function renderGraph(nodes, edges) {
  const container = document.getElementById('graph-network');
  const data = {
    nodes: new vis.DataSet(
      (nodes || []).map((node) => ({
        id: node.id,
        label: node.label,
        title: `${node.type || 'node'} node`,
        color: {
          background: getNodeColor(node.type),
          border: '#e2e8f0',
          highlight: { background: getNodeColor(node.type), border: '#fff' }
        },
        font: { color: '#f8fafc', face: 'Inter, sans-serif' },
        shape: 'dot',
        size: 18
      }))
    ),
    edges: new vis.DataSet(
      (edges || []).map((edge) => ({
        from: edge.from,
        to: edge.to,
        label: edge.label || 'related',
        arrows: edge.arrows || 'to',
        width: Math.min(4, 1 + (edge.weight || 1)),
        color: { color: '#7dd3fc', opacity: 0.9 },
        font: { color: '#dbeafe', size: 12 }
      }))
    )
  };

  const options = {
    interaction: { hover: true, tooltipDelay: 150 },
    physics: {
      enabled: true,
      barnesHut: { gravitationalConstant: -15000, springLength: 180, springConstant: 0.02 }
    },
    edges: { smooth: { type: 'dynamic' } },
    nodes: { shape: 'dot', scaling: { label: { enabled: true } } }
  };

  if (network) {
    network.destroy();
  }

  network = new vis.Network(container, data, options);
}

function getNodeColor(type) {
  const palette = {
    patient: '#fbbf24',
    symptom: '#f87171',
    anatomy: '#4ade80',
    exam: '#60a5fa',
    diagnosis: '#c084fc',
    measurement: '#fbbf24',
    result: '#34d399',
    treatment: '#fb7185',
    unknown: '#94a3b8'
  };

  return palette[type] || '#94a3b8';
}

init();
