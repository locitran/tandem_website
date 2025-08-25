import gradio as gr

def tutorial():
    gr.Markdown(
        """
List of Contents
- [What is single amino acid variant (SAV)?](#what-is-single-amino-acid-variant-sav)
    - [Possible input formats](#possible-input-formats)
    - [models (optional)](#models-optional)
- [Use custom structure (optional)](#use-custom-structure-optional)
- [Output](#output)

# What is single amino acid variant (SAV)?
A SAV refers to a change in a protein's primary sequence caused by a nucleotide substitution \
that alters the encoded amino acid.

## Possible input formats

We can query a SAV, a batch of SAVs, a UniPort ID, or UniProt ID with mutation site. 
A SAV should be formatted as `UniPort ID`, `position`, `wt aa`, `mut aa` \
    ("wt" and "mut" refer to wild-type and mutant), where `position` is \
    the place that mutated amino acid (aa) is introduced.

    *   1 SAV: `O14508 52 S N'`
    *   Batch of SAVs: `O14508 52 S N, A4D2B0 114 H N`
    *   UniProt ID: `P29033`
    *   UniProt ID with mutation site: `P29033 10`


## `models` (optional)

Default is None, it means that we will use the general disease model, TANDEM-DIMPLE, stored at [models/different_number_of_layers/20250423-1234-tandem/n_hidden-5](../models/different_number_of_layers/20250423-1234-tandem/n_hidden-5).

Besides TANDEM-DIMPLE, we can also use transfer-learned models for specific diseases, such as GJB2 and RYR1.
*   GJB2:
    ```python
    models = '../models/transfer_learning_GJB2'
    ```
*   RYR1:
    ```python
    models = '../models/TransferLearning_RYR1'
    ```

## Use custom structure (optional)

Custom structure is provided, we will use the custom structure to map the SAV and \
    calculate structural dynamics features. `custom_PDB` could be a structure file \
    in `.cif` or `.pdb` format, or a PDB ID that can be downloaded from the PDB database.


If custom structure is from Alphafold2 database (in `.pdb` format), it should be started with `AF-`. 
If custom structure is a Alphafold3 predicted structure (in `.cif` format), it should contain `alphafoldserver.com/output-terms` in the first line of the file.
If custom structure is a structure file, ConSurf will compute the conservation score (slower); if it’s a PDB ID, the score is fetched from the ConSurf database (faster).

# Output

## `log.txt`

Take a look in case of error. It contains the log of the program.
Example: [examples/log.txt](../examples/log.txt)

## `SAVs.txt`

This file contains the list of SAVs that are used in the job, separated by new lines.
It is generated from the input query.

## `job_name-Uniprot2PDB.txt`

This file contains the mapping SAVs to PDB structures.

| SAV_coords        | Unique_SAV_coords | Asymmetric_PDB_coords | BioUnit_PDB_coords    | OPM_PDB_coords     | Asymmetric_PDB_resolved_length |
|------------------|-------------------|------------------------|------------------------|--------------------|-------------------------------|
| P29033 52 V A     | P29033 52 V A      | 2ZW3 A 52 V            | 2ZW3 A 52 V 1          | 2ZW3 A 52 V        | 216                           |

*   `SAV_coords`: SAV coordinates in the input query.
*   `Unique_SAV_coords`: Unique SAV coordinates in the input query, in case input UniProt ID is obsolete.
*   `Asymmetric_PDB_coords`: Coordinates of Asymmetric Unit of the PDB structure.
*   `BioUnit_PDB_coords`: Coordinates of Biological Unit of the PDB structure.
*   `OPM_PDB_coords`: Coordinates of Available OPM structure for given PDB ID.
*   `Asymmetric_PDB_resolved_length`: Length of the resolved structure in the asymmetric unit.

## `job_name-features.csv`
This file contains the features of the SAVs in the job. The first column is SAV_coords, and the rest are features, 33 features supposedly, which then are the input of model inference.

## `job_name-report.txt`
Predicted results are stored in this file. 

| SAVs             | Probability | Decision   | Voting |
|------------------|-------------|------------|--------|
| P29033 52 V A     | 0.3384      | Benign     | 100.0  |

*   `SAVs`: SAV coordinates in the input query.
*   `Probability`: Pathogenicity probability of the SAV.
*   `Decision`: Pathogenic or Benign. 
*   `Voting`: Percentage of voting for the decision.

## `job_name-full_predictions.txt`
Detailed predictions of each model are stored in this file.

| SAVs             | TANDEM_0 | TANDEM_1 | TANDEM_2 | TANDEM_3 | TANDEM_4 |
|------------------|----------|----------|----------|----------|----------|
| P29033 52 V A     | 0.3451   | 0.3731   | 0.3031   | 0.3156   | 0.3551   |

# Model construction

## Protein features descriptions

| **Category** | **Feature**                      | **Description**                                                                                 | **Reference** |
|--------------|----------------------------------|-------------------------------------------------------------------------------------------------|--------------|
| **Dynamics** | λ₁, λ₂                           | 1st and 2nd GNM eigenvalues                                                                     |              |
|              | ‖V₁ᵢ‖, ‖V₂ᵢ‖                     | Magnitude of residue *i* in 1st and 2nd GNM slowest modes                                       |              |
|              | rank(‖V₁ᵢ‖), rank(‖V₂ᵢ‖)         | Rank of ‖V₁ᵢ‖ and ‖V₂ᵢ‖                                                                         |              |
|              | rank(‖Cᵢᵢ‖)                       | Rank of GNM fluctuation variance of residue *i*                                                |              |
|              | Effectiveness*                   | Ability of a residue to sense and transmit mechanical signals                                   | Atilgan & Atilgan, 2009 |
|              | Stiffness*                       | Residue’s resistance to uniaxial tension                                                        | Eyal & Bahar, 2008 |
| **Structure**| Lside, ΔLside                    | Side chain length and mutation-induced change                                                   |              |
|              | %Loop, %Helix, %Sheet            | Percentage of secondary structure                                                               | Kabsch & Sander, 1983 |
|              | Disorderliness                   | Predicted intrinsic disorder                                                                    | Yang et al., 2005 |
|              | SA                               | Relative solvent accessibility                                                                  | Hubbard & Thornton, 1993 |
|              | RG                               | Radius of gyration                                                                              |              |
|              | Dcom                             | Distance to center of mass                                                                      |              |
|              | AG1, AG3, AG5                    | Average residue contacts excluding neighbors within ±1, ±2, or ±3 positions                     |              |
|              | NSS-bond                         | Number of disulfide bonds and mutation-induced change                                           |              |
|              | NH-bond, ΔNH-bond                | Number of hydrogen bonds and mutation-induced change                                            | McDonald & Thornton, 1994 |
| **Sequence & Chemical** | ΔPolarity            | Mutation-induced change in polarity                                                             | Grantham, 1974 |
|              | ΔCharge                          | Mutation-induced change in charge                                                               |              |
|              | ConSurf and ACNR                 | Relative conservation score and average ConSurf scores of neighboring residues                 | Ben Chorin et al., 2020; Goldenberg et al., 2009 |
|              | wtPSIC*, ΔPSIC*                  | Position-specific evolutionary conservation and mutation-induced change                         | Sunyaev et al., 1999 |
|              | BLOSUM62*                        | Amino acid substitution score                                                                   | Henikoff & Henikoff, 1992 |
|              | Entropy*, ranked MI*             | Avg. Shannon entropy and ranked mutual information from Pfam MSAs                               | Dunn et al., 2008; Martin et al., 2005 |

## Model architecture

| **Hyperparameter**                      | **Value**                         |
|----------------------------------------|-----------------------------------|
| Data preprocessing                     | Z-normalization                   |
| Batch size                             | 300                               |
| Weight initialization technique        | Xavier uniform                    |
| Number of input neurons                | 33                                |
| Number of hidden neurons               | 33, 33, 33, 33, 10                |
| Number of hidden layers                | 5                                 |
| Activation function at hidden layer    | GeLU                              |
| Number of output neurons               | 2                                 |
| Activation function at output layer    | Softmax                           |
| Early stop                             | 50 (start from epoch 50)          |
| Loss function                          | Cross entropy                     |
| Optimization algorithm                 | Nadam                             |
| Learning rate                          | 5e-5                              |
| Regularization                         | L2 (1e-4)                         |
| Number of iterations/epochs            | 300                               |


sádasd
ád
ád
á
d
        """



    )
