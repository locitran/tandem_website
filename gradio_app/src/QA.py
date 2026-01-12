import gradio as gr
def qa(mount_point):
    html_str = f"""
        <div class="qa-container">

            <h2>TANDEM-DIMPLE Webserver - Q&amp;A</h2>

            <div class="q1-item">
                <div class="q1-text">
                    <h3>Q1: What is a single amino acid variant (SAV)?</h3>
                    <p>
                        A SAV refers to a change in a protein's primary sequence caused by 
                        a nucleotide substitution that alters the encoded amino acid. 
                        TANDEM website records each SAV using the UniProt ID followed by 
                        the amino acid substitution (e.g., P29033 Y217D). 
                        To identify the correct UniProt ID for a gene or protein, please 
                        refer to <a href="https://www.uniprot.org/" target="_blank">UniProt</a>.
                    </p>
                </div>

                <figure class="q1-figure">
                    <img src="{mount_point}/gradio_api/file=assets/images/SAV_definition.png"
                        alt="SAV definition">
                    <figcaption>
                        Figure 1. SAV definition.
                    </figcaption>
                </figure>
            </div>

            <div class="q2-item">
                <h3>Q2: What is the prediction of protein pathogenicity?</h3>
                <p>
                    The protein pathogenicity prediction gives the probability of a specific SAV is 
                    disease-causing (pathogenic) or harmless (benign) by considering its effects 
                    on protein sequence, structure, dynamics, and biological function.
                </p>
                <p>
                    These probabilities can be generated using either <b>TANDEM</b> (gene/disease-general model) 
                    or <b>TANDEM-DIMPLE</b> (gene/disease-specific models), trained on corresponding general 
                    or curated gene/disease-specific datasets.
                </p>
            </div>

            <div class="q3-item">
                <h3>Q3: What is transfer learning?</h3>
                <p>
                    Transfer learning is a machine-learning strategy in which a model pretrained on a large, 
                    general dataset is further fine-tuned using a smaller, gene/disease-specific dataset. 
                    This approach leverages previously learned knowledge to improve prediction accuracy for 
                    specific genes or diseases, especially when labeled data are limited.
                </p>
            </div>

            <div class="q4-item">
                <h3>Q4: What is SHAP analysis?</h3>
                <p>
                    SHAP (SHapley Additive exPlanations) analysis is a model-interpretability method 
                    that explains how each input feature contributes to a model's prediction. 
                    In the context of protein pathogenicity prediction, SHAP analysis shows 
                    which features (e.g., sequence & chemical, structure, or dynamical features) 
                    push a variant's prediction toward pathogenic or benign. 
                    This helps users understand why a specific SAV receives a particular predicted probability, 
                    improving transparency and biological interpretability of the model's decisions.
                </p>
            </div>

            <div class="q5-item">
                <h3>Q5: What features are used in TANDEM-DIMPLE?</h3>
                <p>
                    TBD
                </p>
            </div>

        </div>
    """
    qa_page = gr.HTML(html_str, elem_classes="qa")
    return qa_page