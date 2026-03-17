import gradio as gr


html = """
<div class="qa-test">
  <p>
    TANDEM models were trained using deep neural networks (DNNs) on the R20000 set with the TANDEM feature set
    (<a
      href="#"
      class="qa-inline-trigger"
      aria-controls="r20000-help"
      onclick="
        const box = document.getElementById('r20000-help');
        if (!box) return false;
        box.classList.toggle('is-open');
        this.setAttribute('aria-expanded', box.classList.contains('is-open') ? 'true' : 'false');
        return false;
      "
    >?</a>). The input features were standardized prior to training.
  </p>

  <div id="r20000-help" class="qa-inline-note-body">
    Taken from the Rhapsody (Ponzoni et al., 2020), the 20,361 clinically annotated SAVs of 2,423 genes comprises
    13,626 pathogenic and 6,735 benign variants, referred as R20000 set. The dataset integrates information from
    five publicly available datasets with refined annotations and pathogenic/benign labels using three well-known
    databases UniProtKB (UniProt, 2023), ClinVar (Landrum et al., 2020), and HuVarBase (Ganesan et al., 2019).
    All SAVs have the corresponding UniProt IDs, including a total of 2,423 UniProt protein sequences, each of
    which can harbor one or multiple SAVs.
  </div>

  <p>
    Second line for comparison. If the note works, the sentence above should remain inline and the help box should open below it.
  </p>
</div>
"""


css = """
.qa-test {
  max-width: 980px;
  margin: 0 auto;
  padding: 24px;
  font-family: Helvetica, Arial, sans-serif;
  font-size: 20px;
  line-height: 1.8;
  color: var(--body-text-color);
}

.qa-test p {
  margin: 0 0 18px;
}

.qa-inline-trigger {
  cursor: pointer;
  display: inline;
  border: 0;
  background: transparent;
  font-size: 0.98em;
  font-weight: 600;
  line-height: inherit;
  user-select: none;
  color: #0d6efd;
  text-decoration: underline;
  text-underline-offset: 0.08em;
}

.qa-inline-trigger:hover,
.qa-inline-trigger:focus-visible {
  color: #0a58ca;
  outline: none;
}

.qa-inline-note-body {
  display: none;
  margin: -6px 0 12px;
  padding: 0.35rem 0.5rem;
  border: 1px solid #6c757d;
  border-radius: 0.375rem;
  background: rgba(13, 202, 240, 0.18);
  font-size: 0.98rem;
  line-height: 1.65;
  color: var(--body-text-color);
  max-width: 860px;
}

.qa-inline-note-body.is-open {
  display: block;
}

.dark .qa-inline-trigger {
  color: #66b3ff;
}

.dark .qa-inline-trigger:hover,
.dark .qa-inline-trigger:focus-visible {
  color: #8ec5ff;
}

.dark .qa-inline-note-body {
  background: rgba(13, 202, 240, 0.12);
  border-color: rgba(173, 181, 189, 0.55);
}
"""


with gr.Blocks(css=css, title="Inline Help Test") as demo:
    gr.Markdown("## Inline Help Test")
    gr.HTML(html)


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7867)
