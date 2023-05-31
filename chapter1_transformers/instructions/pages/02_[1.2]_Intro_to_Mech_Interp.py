
import os, sys
from pathlib import Path
chapter = r"chapter1_transformers"
instructions_dir = Path(f"{os.getcwd().split(chapter)[0]}/{chapter}/instructions").resolve()
if str(instructions_dir) not in sys.path: sys.path.append(str(instructions_dir))
os.chdir(instructions_dir)

import streamlit as st
import st_dependencies

st_dependencies.styling()

import platform
is_local = (platform.processor() != "")

def section_0():

    st.sidebar.markdown(r"""

## Table of Contents

<ul class="contents">
    <li class='margtop'><a class='contents-el' href='#introduction'>Introduction</a></li>
    <li class='margtop'><a class='contents-el' href='#content-learning-objectives'>Content & Learning Objectives</a></li>
    <li class='margtop'><a class='contents-el' href='#setup'>Setup</a></li>
</ul></li>""", unsafe_allow_html=True)

    st.markdown(r"""

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/lens2.png" width="350">


Colab: [**exercises**](https://colab.research.google.com/drive/1w9zCWpE7xd1sDuMT_rsjARfFozeWiKF4) | [**solutions**](https://colab.research.google.com/drive/10tzGmOCQb3LoDB69vPFw71DV2d395hJl)

Please send any problems / bugs on the `#errata` channel in the [Slack group](https://join.slack.com/t/arena-la82367/shared_invite/zt-1uvoagohe-JUv9xB7Vr143pdx1UBPrzQ), and ask any questions on the dedicated channels for this chapter of material.

You can toggle dark mode from the buttons on the top-right of this page.


# [1.2] TransformerLens & induction circuits


## Introduction


These pages are designed to get you introduced to Neel's **TransformerLens** library.

Most of the sections are constructed in the following way:

1. A particular feature of TransformerLens is introduced. 
2. You are given an exercise, in which you have to apply the feature. 

The running theme of the exercises is **induction circuits**. Induction circuits are a particular type of circuit in a transformer, which can perform basic in-context learning. You should read the [corresponding section of Neel's glossary](https://dynalist.io/d/n2ZWtnoYHrU1s4vnFSAQ519J#z=_Jzi6YHRHKP1JziwdE02qdYZ), before continuing. This [LessWrong post](https://www.lesswrong.com/posts/TvrfY4c9eaGLeyDkE/induction-heads-illustrated) might also help; it contains some diagrams (like the one below) which walk through the induction mechanism step by step.

Each exercise will have a difficulty and importance rating out of 5, as well as an estimated maximum time you should spend on these exercises and sometimes a short annotation. You should interpret the ratings & time estimates relatively (e.g. if you find yourself spending about 50% longer on the exercises than the time estimates, adjust accordingly). Please do skip exercises / look at solutions if you don't feel like they're important enough to be worth doing, and you'd rather get to the good stuff!


<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/kcomp_diagram.png" width="1000">


## Content & Learning Objectives


#### 1️⃣ TransformerLens: Introduction

This section is designed to get you up to speed with the TransformerLens library. You'll learn how to load and run models, and learn about the shared architecture template for all of these models (the latter of which should be familiar to you if you've already done the exercises that come before these, since many of the same design principles are followed).

> ##### Learning objectives
> 
> - Load and run a `HookedTransformer` model
> - Understand the basic architecture of these models
> - Use the model's tokenizer to convert text to tokens, and vice versa
> - Know how to cache activations, and to access activations from the cache
> - Use `circuitsvis` to visualise attention heads

#### 2️⃣ Finding induction heads

Here, you'll learn about induction heads, how they work and why they are important. You'll also learn how to identify them from the characteristic induction head stripe in their attention patterns when the model input is a repeating sequence.

> ##### Learning objectives
> 
> - Understand what induction heads are, and the algorithm they are implementing
> - Inspect activation patterns to identify basic attention head patterns, and write your own functions to detect attention heads for you
> - Identify induction heads by looking at the attention patterns produced from a repeating random sequence

#### 3️⃣ TransformerLens: Hooks

Next, you'll learn about hooks, which are a great feature of TransformerLens allowing you to access and intervene on activations within the model. We will mainly focus on the basics of hooks and using them to access activations (we'll mainly save the causal interventions for the later IOI exercises). You will also build some tools to perform logit attribution within your model, so you can identify which components are responsible for your model's performance on certain tasks.

> ##### Learning objectives
> 
> - Understand what hooks are, and how they are used in TransformerLens
> - Use hooks to access activations, process the results, and write them to an external tensor
> - Build tools to perform attribution, i.e. detecting which components of your model are responsible for performance on a given task
> - Understand how hooks can be used to perform basic interventions like **ablation**

#### 4️⃣ Reverse-engineering induction circuits

Lastly, these exercises show you how you can reverse-engineer a circuit by looking directly at a transformer's weights (which can be considered a "gold standard" of interpretability; something not possible in every situation). You'll examine QK and OV circuits by multiplying through matrices (and learn how the FactoredMatrix class makes matrices like these much easier to analyse). You'll also look for evidence of composition between two induction heads, and once you've found it then you'll investigate the functionality of the full circuit formed from this composition.

> ##### Learning objectives
> 
> - Understand the difference between investigating a circuit by looking at activtion patterns, and reverse-engineering a circuit by looking directly at the weights
> - Use the factored matrix class to inspect the QK and OV circuits within an induction circuit
> - Perform further exploration of induction circuits: composition scores, and targeted ablations


## Setup


```python
import os
import sys
import plotly.express as px
import torch as t
from torch import Tensor
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
import numpy as np
import einops
from jaxtyping import Int, Float
from typing import List, Optional, Tuple
import functools
from tqdm import tqdm
from IPython.display import display
import webbrowser
import gdown
from transformer_lens.hook_points import HookPoint
from transformer_lens import utils, HookedTransformer, HookedTransformerConfig, FactoredMatrix, ActivationCache
import circuitsvis as cv

# Make sure exercises are in the path
chapter = r"chapter1_transformers"
exercises_dir = Path(f"{os.getcwd().split(chapter)[0]}/{chapter}/exercises").resolve()
section_dir = (exercises_dir / "part2_intro_to_mech_interp").resolve()
if str(exercises_dir) not in sys.path: sys.path.append(str(exercises_dir))

from plotly_utils import imshow, hist, plot_comp_scores, plot_logit_attribution, plot_loss_difference
from part1_transformer_from_scratch.solutions import get_log_probs
import part2_intro_to_mech_interp.tests as tests

# Saves computation time, since we don't need it for the contents of this notebook
t.set_grad_enabled(False)

device = t.device("cuda" if t.cuda.is_available() else "cpu")

MAIN = __name__ == "__main__"

```



""", unsafe_allow_html=True)


def section_1():

    st.sidebar.markdown(r"""

## Table of Contents

<ul class="contents">
    <li class='margtop'><a class='contents-el' href='#introduction'>Introduction</a></li>
    <li class='margtop'><a class='contents-el' href='#loading-and-running-models'>Loading and Running Models</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#hookedtransformerconfig'>HookedTransformerConfig</a></li>
        <li><a class='contents-el' href='#exercise-inspect-your-model'><b>Exercise</b> - inspect your model</a></li>
        <li><a class='contents-el' href='#running-your-model'>Running your model</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#transformer-architecture'>Transformer architecture</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#parameters-and-activations'>Parameters and Activations</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#tokenization'>Tokenization</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#exercise-how-many-words-does-your-model-guess-correctly'><b>Exercise</b> - how many words does your model guess correctly?</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#caching-all-activations'>Caching all Activations</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#exercise-verify-activations'><b>Exercise</b> - verify activations</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#visualising-attention-heads'>Visualising Attention Heads</a></li>
</ul></li>""", unsafe_allow_html=True)

    st.markdown(r"""

# 1️⃣ TransformerLens: Introduction


> ##### Learning objectives
> 
> - Load and run a `HookedTransformer` model
> - Understand the basic architecture of these models
> - Use the model's tokenizer to convert text to tokens, and vice versa
> - Know how to cache activations, and to access activations from the cache
> - Use `circuitsvis` to visualise attention heads


## Introduction

*Note - most of this is written from the POV of Neel Nanda.*

This is a demo notebook for [TransformerLens](https://github.com/neelnanda-io/TransformerLens), **a library I ([Neel Nanda](https://www.neelnanda.io/)) wrote for doing [mechanistic interpretability](https://distill.pub/2020/circuits/zoom-in/) of GPT-2 Style language models.** The goal of mechanistic interpretability is to take a trained model and reverse engineer the algorithms the model learned during training from its weights. It is a fact about the world today that we have computer programs that can essentially speak English at a human level (GPT-3, PaLM, etc), yet we have no idea how they work nor how to write one ourselves. This offends me greatly, and I would like to solve this! Mechanistic interpretability is a very young and small field, and there are a *lot* of open problems - if you would like to help, please try working on one! **Check out my [list of concrete open problems](https://docs.google.com/document/d/1WONBzNqfKIxERejrrPlQMyKqg7jSFW92x5UMXNrMdPo/edit#) to figure out where to start.**

I wrote this library because after I left the Anthropic interpretability team and started doing independent research, I got extremely frustrated by the state of open source tooling. There's a lot of excellent infrastructure like HuggingFace and DeepSpeed to *use* or *train* models, but very little to dig into their internals and reverse engineer how they work. **This library tries to solve that**, and to make it easy to get into the field even if you don't work at an industry org with real infrastructure! The core features were heavily inspired by [Anthropic's excellent Garcon tool](https://transformer-circuits.pub/2021/garcon/index.html). Credit to Nelson Elhage and Chris Olah for building Garcon and showing me the value of good infrastructure for accelerating exploratory research!

The core design principle I've followed is to enable exploratory analysis - one of the most fun parts of mechanistic interpretability compared to normal ML is the extremely short feedback loops! The point of this library is to keep the gap between having an experiment idea and seeing the results as small as possible, to make it easy for **research to feel like play** and to enter a flow state. This notebook demonstrates how the library works and how to use it, but if you want to see how well it works for exploratory research, check out [my notebook analysing Indirect Objection Identification](https://github.com/neelnanda-io/TransformerLens/blob/main/Exploratory_Analysis_Demo.ipynb) or [my recording of myself doing research](https://www.youtube.com/watch?v=yo4QvDn-vsU)!


## Loading and Running Models

TransformerLens comes loaded with >40 open source GPT-style models. You can load any of them in with `HookedTransformer.from_pretrained(MODEL_NAME)`. For this demo notebook we'll look at GPT-2 Small, an 80M parameter model, see the Available Models section for info on the rest.




```python

if MAIN:
    gpt2_small: HookedTransformer = HookedTransformer.from_pretrained("gpt2-small")

```

### HookedTransformerConfig

Alternatively, you can define a config object, then call `HookedTransformer.from_config(cfg)` to define your model. This is particularly useful when you want to have finer control over the architecture of your model. We'll see an example of this in the next section, when we define an attention-only model to study induction heads.

Even if you don't define your model in this way, you can still access the config object through the `cfg` attribute of the model.


### Exercise - inspect your model

```c
Difficulty: 🟠⚪⚪⚪⚪
Importance: 🟠🟠🟠⚪⚪
```

Use `gpt2_small.cfg` to find the following, for your GPT-2 Small model:

* Number of layers
* Number of heads per layer
* Maximum context window

You might have to check out the documentation page for some of these. If you're in VSCode then you can reach it by right-clicking on `HookedTransformerConfig` in the sidebar, and choosing "Go to definition". If you're in Colab, then you can read the [GitHub page](https://github.com/neelnanda-io/TransformerLens).

<details>
<summary>Solution</summary>

The following parameters in the config object give you the answers:

```
cfg.n_layers == 12
cfg.n_heads == 12
cfg.n_ctx == 1024
```

</details>


### Running your model

Models can be run on a single string or a tensor of tokens (shape: `[batch, position]`, all integers). The possible return types are: 

* `"logits"` (shape `[batch, position, d_vocab]`, floats), 
* `"loss"` (the cross-entropy loss when predicting the next token), 
* `"both"` (a tuple of `(logits, loss)`) 
* `None` (run the model, but don't calculate the logits - this is faster when we only want to use intermediate activations)


```python

if MAIN:
    model_description_text = '''## Loading Models
    
    HookedTransformer comes loaded with >40 open source GPT-style models. You can load any of them in with `HookedTransformer.from_pretrained(MODEL_NAME)`. Each model is loaded into the consistent HookedTransformer architecture, designed to be clean, consistent and interpretability-friendly. 
    
    For this demo notebook we'll look at GPT-2 Small, an 80M parameter model. To try the model the model out, let's find the loss on this paragraph!'''
    
    loss = gpt2_small(model_description_text, return_type="loss")
    print("Model loss:", loss)

```

## Transformer architecture

HookedTransformer is a somewhat adapted GPT-2 architecture, but is computationally identical. The most significant changes are to the internal structure of the attention heads:

* The weights `W_K`, `W_Q`, `W_V` mapping the residual stream to queries, keys and values are 3 separate matrices, rather than big concatenated one.
* The weight matrices `W_K`, `W_Q`, `W_V`, `W_O` and activations have separate `head_index` and `d_head` axes, rather than flattening them into one big axis.
    * The activations all have shape `[batch, position, head_index, d_head]`.
    * `W_K`, `W_Q`, `W_V` have shape `[head_index, d_model, d_head]` and `W_O` has shape `[head_index, d_head, d_model]`
* **Important - we generally follow the convention that weight matrices multiply on the right rather than the left.** In other words, they have shape `[input, output]`, and we have `new_activation = old_activation @ weights + bias`.
    * Click the dropdown below for examples of this, if it seems unintuitive.

<details>
<summary>Examples of matrix multiplication in our model</summary>

* **Query matrices**
    * Each query matrix `W_Q` for a particular layer and head has shape `[d_model, d_head]`. 
    * So if a vector `x` in the residual stream has length `d_model`, then the corresponding query vector is `x @ W_Q`, which has length `d_head`.
* **Embedding matrix**
    * The embedding matrix `W_E` has shape `[d_vocab, d_model]`. 
    * So if `A` is a one-hot-encoded vector of length `d_vocab` corresponding to a particular token, then the embedding vector for this token is `A @ W_E`, which has length `d_model`.

</details>

The actual code is a bit of a mess, as there's a variety of Boolean flags to make it consistent with the various different model families in TransformerLens - to understand it and the internal structure, I instead recommend reading the code in [CleanTransformerDemo](https://colab.research.google.com/github/neelnanda-io/TransformerLens/blob/clean-transformer-demo/Clean_Transformer_Demo.ipynb).




### Parameters and Activations

It's important to distinguish between parameters and activations in the model.

* **Parameters** are the weights and biases that are learned during training.
    * These don't change when the model input changes.
    * They can be accessed direction fromm the model, e.g. `model.W_E` for the embedding matrix.
* **Activations** are temporary numbers calculated during a forward pass, that are functions of the input.
    * We can think of these values as only existing for the duration of a single forward pass, and disappearing afterwards.
    * We can use hooks to access these values during a forward pass (more on hooks later), but it doesn't make sense to talk about a model's activations outside the context of some particular input.
    * Attention scores and patterns are activations (this is slightly non-intuitve because they're used in a matrix multiplication with another activation).

The link below shows a diagram of a single layer (called a `TransformerBlock`) for an attention-only model with no biases. Each box corresponds to an **activation** (and also tells you the name of the corresponding hook point, which we will eventually use to access those activations). The red text below each box tells you the shape of the activation (ignoring the batch dimension). Each arrow corresponds to an operation on an activation; where there are **parameters** involved these are labelled on the arrows.

[Link to diagram](https://mermaid.ink/svg/pako:eNrNVsFu2zAM_RVBh7UDYnQLdnKyHIasOfQwFCu2Q10EikXHhmVJkWQ3Sd1_H-U4dR2kQLFDEx0kUibtR_pR1BONFQca0qVhOiV300gSHLZc7DYiOraaSWLdRsD3i0RJF9hsC-Hwm15fTO4MkzZRpgDzQ6g4J5fMOUmUFJvP4yvvOYno7pV-xIJZO4WEQKHdhjxm3KXhF70epJAtU-fF0RFrDxEnoUxogKNFZ2PAZnyuDdxH9EUe86zaI14ow8EETulwqNfEKpFxshAszkcFM8tMNo-aYMZX6DcZN19rvbuPdpF_HXrjSwurAeHzAq0Fxuq9MNaHIAim9-QhDMMmxiCY1IzzusWmrOuwd9J7090k9xMUVo_6y7G9dyz_Nx_5sX5UfXXVV_O-6iOZ21hhXvoPrvuqRkMwsr8566vbvoqvLMWrNIPkR_jif8zf-Z-6QuJUH0cYmQLjnjd-7dNmdkCbx6YmgBNWLYlKSMVECaSC2Clj6y3i3p4eN0GkBBP5q96lfVeGKJwA2mEpemy1LQuiKjDEW9m64Z0qPc69eOrT4k1y3tYrhLk6C3JeH5CTK0e0UbyMHWFCyWXrNSA2ZgIIk5wUzOb1q0Lf53ynfUhYbUQY3W0z3_SiQnaoxBVsXbfHDCJspTNAF8zeZMZNnSPU_DyYcayhde2u68uonLLUDmFiW6ADiheXgmUcL0BPfjuiLoUCIhqiyCFhvpNgn3tG01Jz5uAnz_D8pWHChIUBZaVTvzcypqEzJeyNphnDfl60Vs__ANh9IJM)

The next link is to a diagram of a `TransformerBlock` with full features (including biases, layernorms, and MLPs). Don't worry if not all of this makes sense at first - we'll return to some of the details later. As we work with these transformers, we'll get more comfortable with their architecture.

[Link to diagram](https://mermaid.ink/svg/pako:eNrdV1FP2zAQ_itWpI1tasSIeApdJaYWJqGNIRA8UBS5sdNadeLUdkJbwn_fOUkJ6ZoCm9R2y4N955yT786fz-cHyxeEWq41lDgeoatuP0LwqGRQDPSttopxhJSecfplLxCRthWbU9c5jKd7nSuJIxUIGVL5lQt_3N431p2-VXzGPD7HSnVpgGgY6xm6Z0SP3M_xtDWibDjSRjxaYW1gQcOFdCUlYFHZSKoY8WJJb_vWk9wmLF2gHAhJqLS1iF0nniIlOCNowLE_PgqxHLIof5U70N6HeZ12_rdydvXTytsDxxh_UHTSQsQLwZp_bO-bWeDrnW3b3Vt057pu7qNtdzJMSFZgCxmB973G97FQunIElG16UgW5kl7LBR4doPc0VPFR2T1v0ZruJev17QrK5ah9zGl9KAKeYg6ASTVOI7KCWAiWCGXguJbY1yikOIJosZRBbAczCADJ8u_DuuX95pbs4NliFShvPA7gBtBmlYMArFL-VUJhrSP0Flqgt3Z_1jYwLq2rk7o6rqvGN0_5AihXf3FSV2MwpDKqD57W1XldhU8mXDdQvGKFyUI33rWhznWWAmHSzfFkRDHxGJkaxhi5nktPl3LlfX5QUIJwOkQiQCnmCUUp9bWQKpsD9PlOQF_sx_OsWIIiq4OwHXTLW9HAg5wWIpFSmVuqFoJzCA0YVsCC8ywnpUgM8IW47WO1mbkXhrkX2QTATnaFuSdLzCVCo1gKksAhgrmIhuWsVnE8IRwRFGI1zp6lg0XwC20jnlVOgY8XeXtWcwx4IwId4mlW5iMAWUq7AdA-bSbKmSHKWTYGzOOdIcrfFVoOevHYW1cWOU11kbO2MIJK9qlQBXmbqeG1BZqzsxWa81-UaCGPX1tfNRByJfnyykcule_mbvRiVeMsQs7ykLMoK-6JG70hHqJPjZwFunoBoCpufZu97zXjgoDBYW8iBl0Gq1qWAaW05a1uo17JzXzVC_HdOwQAfxx_720E3eW345-933bNlkFYLSukQH1GLNd6MJD6lh7RkPYtF0RCA2yuArDlHsE0iQnWtEcY1M2WG2CuaMvCiRaXs8i3XC0TujDqMgz7PyytHn8BSKkJUQ)


A few shortctus to make your lives easier when using these models:

* You can index weights like `W_Q` directly from the model via e.g. `model.blocks[0].attn.W_Q` (which gives you the `[nheads, d_model, d_head]` query weights for all heads in layer 0).
    * But an easier way is just to index with `model.W_Q`, which gives you the `[nlayers, nheads, d_model, d_head]` tensor containing **every** query weight in the model.
* Similarly, there exist shortcuts `model.W_E`, `model.W_U` and `model.W_pos` for the embeddings, unembeddings and positional embeddings respectively.
* With models containing MLP layers, you also have `model.W_in` and `model.W_out` for the linear layers.
* The same is true for all biases (e.g. `model.b_Q` for all query biases).


## Tokenization

The tokenizer is stored inside the model, and you can access it using `model.tokenizer`. There are also a few helper methods that call the tokenizer under the hood, for instance:

* `model.to_str_tokens(text)` converts a string into a tensor of tokens-as-strings.
* `model.to_tokens(text)` converts a string into a tensor of tokens.
* `model.to_string(tokens)` converts a tensor of tokens into a string.

Examples of use:


```python

if MAIN:
    print(gpt2_small.to_str_tokens("gpt2"))
    print(gpt2_small.to_tokens("gpt2"))
    print(gpt2_small.to_string([50256, 70, 457, 17]))

```

<details>
<summary>Aside - <code><|endoftext|></code></summary>

A weirdness you may have noticed in the above is that `to_tokens` and `to_str_tokens` added a weird `<|endoftext|>` to the start of each prompt. We encountered this in the previous set of exercises, and noted that this was the **Beginning of Sequence (BOS)** token (which for GPT-2 is also the same as the EOS and PAD tokens - index `50256`.

TransformerLens appends this token by default, and it can easily trip up new users. Notably, **this includes** `model.forward` (which is what's implicitly used when you do eg `model("Hello World")`). You can disable this behaviour by setting the flag `prepend_bos=False` in `to_tokens`, `to_str_tokens`, `model.forward` and any other function that converts strings to multi-token tensors.

`prepend_bos` is a bit of a hack, and I've gone back and forth on what the correct default here is. The reason I do this is that transformers tend to treat the first token weirdly - this doesn't really matter in training (where all inputs are >1000 tokens), but this can be a big issue when investigating short prompts! The reason for this is that attention patterns are a probability distribution and so need to add up to one, so to simulate being "off" they normally look at the first token. Giving them a BOS token lets the heads rest by looking at that, preserving the information in the first "real" token.

Further, *some* models are trained to need a BOS token (OPT and my interpretability-friendly models are, GPT-2 and GPT-Neo are not). But despite GPT-2 not being trained with this, empirically it seems to make interpretability easier.

</details>


### Exercise - how many words does your model guess correctly?

```c
Difficulty: 🟠🟠⚪⚪⚪
Importance: 🟠🟠🟠⚪⚪

You should spend up to ~10 minutes on this exercise.
```

Consider the `model_description_text` you fed into your model above. How many words did your model guess correctly? Which words were correct? 


```python

if MAIN:
    logits: Tensor = gpt2_small(model_description_text, return_type="logits")
    prediction = logits.argmax(dim=-1).squeeze()[:-1]
    # YOUR CODE HERE - get the model's prediction on the text

```

<details>
<summary>Hint</summary>

Use `return_type="logits"` to get the model's predictions, then take argmax across the vocab dimension. Then, compare these predictions with the actual tokens, derived from the `model_description_text`.

Remember, you should be comparing the `[:-1]`th elements of this tensor of predictions with the `[1:]`th elements of the input tokens (because your model's output represents a probability distribution over the *next* token, not the current one).

Also, remember to handle the batch dimension (since `logits`, and the output of `to_tokens`, will both have batch dimensions by default).

</details>

<details>
<summary>Solution </summary>

```python
logits = gpt2_small(model_description_text, return_type="logits")
prediction = logits.argmax(dim=-1).squeeze()[:-1]
true_tokens = gpt2_small.to_tokens(model_description_text).squeeze()[1:]
num_correct = (prediction == true_tokens).sum()

print(f"Model accuracy: {num_correct}/{len(true_tokens)}")
print(f"Correct words: {gpt2_small.to_str_tokens(prediction[prediction == true_tokens])}")
```

The output from this code is:

```
Model accuracy: 32/112
Correct words: ['\n', '\n', 'former', ' with', ' models', '.', ' can', ' of', 'ooked', 'Trans', 'former', '_', 'NAME', '`.', ' model', ' the', 'Trans', 'former', ' to', ' be', ' and', '-', '.', '\n', ' at', 'PT', '-', ',', ' model', ',', "'s", ' the']
```

So the model got 32 out of 112 words correct. Not too bad!
</details>


**Induction heads** are a special kind of attention head which we'll examine a lot more in coming exercises. They allow a model to perform in-context learning of a specific form: generalising from one observation that token `B` follows token `A`, to predict that token `B` will follow `A` in future occurrences of `A`, even if these two tokens had never appeared together in the model's training data.

**Can you see evidence of any induction heads at work, on this text?**

<details>
<summary>Evidence of induction heads</summary>

The evidence for induction heads comes from the fact that the model successfully predicted `'ooked', 'Trans', 'former'` following the token `'H'`. This is because it's the second time that `HookedTransformer` had appeared in this text string, and the model predicted it the second time but not the first. (The model did predict `former` the first time, but we can reasonably assume that `Transformer` is a word this model had already been exposed to during training, so this prediction wouldn't require the induction capability, unlike `HookedTransformer`.)

```python
print(gpt2_small.to_str_tokens("HookedTransformer", prepend_bos=False))     # --> ['H', 'ooked', 'Trans', 'former']
```
</details>


## Caching all Activations

The first basic operation when doing mechanistic interpretability is to break open the black box of the model and look at all of the internal activations of a model. This can be done with `logits, cache = model.run_with_cache(tokens)`. Let's try this out, on the first sentence from the GPT-2 paper.

<details>
<summary>Aside - a note on <code>remove_batch_dim</code></summary>

Every activation inside the model begins with a batch dimension. Here, because we only entered a single batch dimension, that dimension is always length 1 and kinda annoying, so passing in the `remove_batch_dim=True` keyword removes it. 

`gpt2_cache_no_batch_dim = gpt2_cache.remove_batch_dim()` would have achieved the same effect.
</details>


```python

if MAIN:
    gpt2_text = "Natural language processing tasks, such as question answering, machine translation, reading comprehension, and summarization, are typically approached with supervised learning on taskspecific datasets."
    gpt2_tokens = gpt2_small.to_tokens(gpt2_text)
    gpt2_logits, gpt2_cache = gpt2_small.run_with_cache(gpt2_tokens, remove_batch_dim=True)

```

If you inspect the `gpt2_cache` object, you should see that it contains a very large number of keys, each one corresponding to a different activation in the model. You can access the keys by indexing the cache directly, or by a more convenient indexing shorthand. For instance, the code:


```python

if MAIN:
    attn_patterns_layer_0 = gpt2_cache["pattern", 0]

```

returns the same thing as:


```python

if MAIN:
    attn_patterns_layer_0_copy = gpt2_cache["blocks.0.attn.hook_pattern"]
    
    t.testing.assert_close(attn_patterns_layer_0, attn_patterns_layer_0_copy)

```

<details>
<summary>Aside: <code>utils.get_act_name</code></summary>

The reason these are the same is that, under the hood, the first example actually indexes by `utils.get_act_name("pattern", 0)`, which evaluates to `"blocks.0.attn.hook_pattern"`.

In general, `utils.get_act_name` is a useful function for getting the full name of an activation, given its short name and layer number.

You can use the diagram from the **Transformer Architecture** section to help you find activation names.
</details>


### Exercise - verify activations

```c
Difficulty: 🟠🟠🟠⚪⚪
Importance: 🟠🟠🟠⚪⚪

You should spend up to 10-15 minutes on this exercise.

If you're already comfortable implementing things like attention calculations (e.g. having gone through Neel's transformer walkthrough) you can skip this exercise. However, it might serve as a useful refresher.
```

Verify that `hook_q`, `hook_k` and `hook_pattern` are related to each other in the way implied by the diagram. Do this by computing `layer0_pattern_from_cache` (the attention pattern taken directly from the cache, for layer 0) and `layer0_pattern_from_q_and_k` (the attention pattern calculated from `hook_q` and `hook_k`, for layer 0). Remember that attention pattern is the probabilities, so you'll need to scale and softmax appropriately.


```python

if MAIN:
    layer0_pattern_from_cache = gpt2_cache["pattern", 0]
    
    # YOUR CODE HERE - define `layer0_pattern_from_q_and_k` manually, by manually performing the steps of the attention calculation (dot product, masking, scaling, softmax)
    t.testing.assert_close(layer0_pattern_from_cache, layer0_pattern_from_q_and_k)
    print("Tests passed!")

```

<details>
<summary>Hint</summary>

You'll need to use three different cache indexes in all:

* `gpt2_cache["pattern", 0]` to get the attention patterns, which have shape `[seqQ, seqK]`
* `gpt2_cache["q", 0]` to get the query vectors, which have shape `[seqQ, nhead, headsize]`
* `gpt2_cache["k", 0]` to get the key vectors, which have shape `[seqK, nhead, headsize]`

</details>

<details>
<summary>Solution</summary>

```python
q, k = gpt2_cache["q", 0], gpt2_cache["k", 0]
seq, nhead, headsize = q.shape
layer0_attn_scores = einops.einsum(q, k, "seqQ n h, seqK n h -> n seqQ seqK")
mask = t.triu(t.ones((seq, seq), dtype=bool), diagonal=1).to(device)
layer0_attn_scores.masked_fill_(mask, -1e9)
layer0_pattern_from_q_and_k = (layer0_attn_scores / headsize**0.5).softmax(-1)

```
</details>


## Visualising Attention Heads

A key insight from the Mathematical Frameworks paper is that we should focus on interpreting the parts of the model that are intrinsically interpretable - the input tokens, the output logits and the attention patterns. Everything else (the residual stream, keys, queries, values, etc) are compressed intermediate states when calculating meaningful things. So a natural place to start is classifying heads by their attention patterns on various texts.

When doing interpretability, it's always good to begin by visualising your data, rather than taking summary statistics. Summary statistics can be super misleading! But now that we have visualised the attention patterns, we can create some basic summary statistics and use our visualisations to validate them! (Accordingly, being good at web dev/data visualisation is a surprisingly useful skillset! Neural networks are very high-dimensional object.)

Let's visualize the attention pattern of all the heads in layer 0, using [Alan Cooney's CircuitsVis library](https://github.com/alan-cooney/CircuitsVis) (based on Anthropic's PySvelte library). If you did the previous set of exercises, you'll have seen this library before.

We will use the function `cv.attention.attention_patterns`, which takes two important arguments:

* `attention`: Attention head activations. 
    * This should be a tensor of shape `[nhead, seq_dest, seq_src]`, i.e. the `[i, :, :]`th element is the grid of attention patterns (probabilities) for the `i`th attention head.
    * We get this by indexing our `gpt2_cache` object.
* `tokens`: List of tokens (e.g. `["A", "person"]`). 
    * Sequence length must match that inferred from `attention`.
    * This is used to label the grid.
    * We get this by using the `gpt2_small.to_str_tokens` method.

(Another optional argument is `attention_head_names`, which is useful if you don't just want the heads to show up as "Head 0", "Head 1", ... in the visualisation. Also, note that we can use `cv.attention.attention_patterns` too, which has the same syntax but presents information differently, and can be more helpful in some cases.)

<details>
<summary>Help - my <code>attention_heads</code> plots are behaving weirdly (e.g. they continually shrink after I plot them).</summary>

This seems to be a bug in `circuitsvis` - on VSCode, the attention head plots continually shrink in size.

Until this is fixed, one way to get around it is to open the plots in your browser. You can do this inline with the `webbrowser` library:

```python
attn_heads = cv.attention.attention_heads(
    tokens=gpt2_str_tokens, 
    attention=attention_pattern,
    attention_head_names=[f"L0H{i}" for i in range(12)],
)

path = "attn_heads.html"

with open(path, "w") as f:
    f.write(str(attn_heads))

webbrowser.open(path)
```

To check exactly where this is getting saved, you can print your current working directory with `os.getcwd()`.
</details>

This visualization is interactive! Try hovering over a token or head, and click to lock. The grid on the top left and for each head is the attention pattern as a destination position by source position grid. It's lower triangular because GPT-2 has **causal attention**, attention can only look backwards, so information can only move forwards in the network.


```python

if MAIN:
    print(type(gpt2_cache))
    attention_pattern = gpt2_cache["pattern", 0, "attn"]
    print(attention_pattern.shape)
    gpt2_str_tokens = gpt2_small.to_str_tokens(gpt2_text)
    
    print("Layer 0 Head Attention Patterns:")
    display(cv.attention.attention_patterns(
        tokens=gpt2_str_tokens, 
        attention=attention_pattern,
        attention_head_names=[f"L0H{i}" for i in range(12)],
    ))

```

Hover over heads to see the attention patterns; click on a head to lock it. Hover over each token to see which other tokens it attends to (or which other tokens attend to it - you can see this by changing the dropdown to `Destination <- Source`).




""", unsafe_allow_html=True)


def section_2():

    st.sidebar.markdown(r"""

## Table of Contents

<ul class="contents">
    <li class='margtop'><a class='contents-el' href='#introducing-our-toy-attention-only-model'>Introducing Our Toy Attention-Only Model</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#exercise-visualise-attention-patterns'><b>Exercise</b> - visualise attention patterns</a></li>
        <li><a class='contents-el' href='#exercise-write-your-own-detectors'><b>Exercise</b> - write your own detectors</a></li>
        <li><a class='contents-el' href='#bonus-try-different-text'>Bonus - try different text</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#what-are-induction-heads'>What are induction heads?</a></li>
    <li class='margtop'><a class='contents-el' href='#checking-for-the-induction-capability'>Checking for the induction capability</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#exercise-plot-per-token-loss-on-repeated-sequence'><b>Exercise</b> - plot per-token loss on repeated sequence</a></li>
        <li><a class='contents-el' href='#looking-for-induction-attention-patterns'>Looking for Induction Attention Patterns</a></li>
        <li><a class='contents-el' href='#exercise-make-an-induction-head-detector'><b>Exercise</b> - make an induction-head detector</a></li>
</ul></li>""", unsafe_allow_html=True)

    st.markdown(r"""

# 2️⃣ Finding induction heads


> ##### Learning objectives
> 
> - Understand what induction heads are, and the algorithm they are implementing
> - Inspect activation patterns to identify basic attention head patterns, and write your own functions to detect attention heads for you
> - Identify induction heads by looking at the attention patterns produced from a repeating random sequence


## Introducing Our Toy Attention-Only Model

Here we introduce a toy 2L attention-only transformer trained specifically for today. Some changes to make them easier to interpret:
- It has only attention blocks.
- The positional embeddings are only added to each key and query vector in the attention layers as opposed to the token embeddings (meaning that the residual stream can't directly encode positional information).
    - This turns out to make it *way* easier for induction heads to form, it happens 2-3x times earlier - [see the comparison of two training runs](https://wandb.ai/mechanistic-interpretability/attn-only/reports/loss_ewma-22-08-24-11-08-83---VmlldzoyNTI0MDMz?accessToken=8ap8ir6y072uqa4f9uinotdtrwmoa8d8k2je4ec0lyasf1jcm3mtdh37ouijgdbm) here. (The bump in each curve is the formation of induction heads.)
    - The argument that does this below is `positional_embedding_type="shortformer"`.
- It has no MLP layers, no LayerNorms, and no biases.
- There are separate embed and unembed matrices (i.e. the weights are not tied).

We now define our model with a `HookedTransformerConfig` object. This is similar to the `Config` object we used in the previous set of exercises, although it has a lot more features. You can look at the documentation page (Right-click, "Go to Definition" in VSCode) to seee what the different arguments do.


```python

if MAIN:
    cfg = HookedTransformerConfig(
        d_model=768,
        d_head=64,
        n_heads=12,
        n_layers=2,
        n_ctx=2048,
        d_vocab=50278,
        attention_dir="causal",
        attn_only=True, # defaults to False
        tokenizer_name="EleutherAI/gpt-neox-20b", 
        seed=398,
        use_attn_result=True,
        normalization_type=None, # defaults to "LN", i.e. layernorm with weights & biases
        positional_embedding_type="shortformer"
    )

```

<details>
<summary>An aside about tokenizers</summary>

In the last section, we defined a tokenizer explicitly, and passed it into our model. But here, we just pass a tokenizer name. The model automatically creates a tokenizer for us (under the hood, it calls `AutoTokenizer.from_pretrained(tokenizer_name)`).
</details>

Below, you'll load in your weights, with some useful boilerplate code to download files from Google Drive and store them in a specified filepath:


```python

if MAIN:
    weights_dir = (section_dir / "attn_only_2L_half.pth").resolve()
    
    if not weights_dir.exists():
        url = "https://drive.google.com/uc?id=1vcZLJnJoYKQs-2KOjkd6LvHZrkSdoxhu"
        output = str(weights_dir)
        gdown.download(url, output)

```

Finally, we'll create our model and load in the weights:


```python

if MAIN:
    model = HookedTransformer(cfg)
    pretrained_weights = t.load(weights_dir, map_location=device)
    model.load_state_dict(pretrained_weights)

```

Use the [diagram at this link](https://mermaid.ink/svg/pako:eNrNVsFu2zAM_RVBh7UDYnQLdnKyHIasOfQwFCu2Q10EikXHhmVJkWQ3Sd1_H-U4dR2kQLFDEx0kUibtR_pR1BONFQca0qVhOiV300gSHLZc7DYiOraaSWLdRsD3i0RJF9hsC-Hwm15fTO4MkzZRpgDzQ6g4J5fMOUmUFJvP4yvvOYno7pV-xIJZO4WEQKHdhjxm3KXhF70epJAtU-fF0RFrDxEnoUxogKNFZ2PAZnyuDdxH9EUe86zaI14ow8EETulwqNfEKpFxshAszkcFM8tMNo-aYMZX6DcZN19rvbuPdpF_HXrjSwurAeHzAq0Fxuq9MNaHIAim9-QhDMMmxiCY1IzzusWmrOuwd9J7090k9xMUVo_6y7G9dyz_Nx_5sX5UfXXVV_O-6iOZ21hhXvoPrvuqRkMwsr8566vbvoqvLMWrNIPkR_jif8zf-Z-6QuJUH0cYmQLjnjd-7dNmdkCbx6YmgBNWLYlKSMVECaSC2Clj6y3i3p4eN0GkBBP5q96lfVeGKJwA2mEpemy1LQuiKjDEW9m64Z0qPc69eOrT4k1y3tYrhLk6C3JeH5CTK0e0UbyMHWFCyWXrNSA2ZgIIk5wUzOb1q0Lf53ynfUhYbUQY3W0z3_SiQnaoxBVsXbfHDCJspTNAF8zeZMZNnSPU_DyYcayhde2u68uonLLUDmFiW6ADiheXgmUcL0BPfjuiLoUCIhqiyCFhvpNgn3tG01Jz5uAnz_D8pWHChIUBZaVTvzcypqEzJeyNphnDfl60Vs__ANh9IJM) to remind yourself of the relevant hook names.


### Exercise - visualise attention patterns

```c
Difficulty: 🟠🟠⚪⚪⚪
Importance: 🟠🟠🟠⚪⚪

You should spend up to ~10 minutes on this exercise.

It's important to be comfortable using circuitsvis, and the cache object.
```

*This exercise should be very quick - you can reuse code from the previous section. You should look at the solution if you're still stuck after 5-10 minutes.*

Visualise the attention patterns for both layers of your model, on the following prompt:


```python

if MAIN:
    text = "We think that powerful, significantly superhuman machine intelligence is more likely than not to be created this century. If current machine learning techniques were scaled up to this level, we think they would by default produce systems that are deceptive or manipulative, and that no solid plans are known for how to avoid this."
    
    logits, cache = model.run_with_cache(text, remove_batch_dim=True)

```

*(Note that we've run the model on the string `text`, rather than on tokens like we did previously when creating a cache - this is something that `HookedTransformer` allows.)*

Inspect the attention patterns. What do you notice about the attention heads? 

You should spot three relatively distinctive basic patterns, which occur in multiple heads. What are these patterns, and can you guess why they might be present?

<details>
<summary>Aside - what to do if your plots won't show up</summary>

A common mistake is to fail to pass the tokens in as arguments. If you do this, your attention patterns won't render.

If this isn't the problem, then it might be an issue with the Circuitsvis library.Rather than plotting inline, you can do the following, and then open in your browser from the left-hand file explorer menu of VSCode:
</details>


```python

if MAIN:
    # YOUR CODE HERE - visualize attention

```

<details>
<summary>Solution </summary>

We visualise attention patterns with the following code:

```python
str_tokens = model.to_str_tokens(text)
for layer in range(model.cfg.n_layers):
    attention_pattern = cache["pattern", layer]
    display(cv.attention.attention_patterns(tokens=str_tokens, attention=attention_pattern))
```

We notice that there are three basic patterns which repeat quite frequently:

* `prev_token_heads`, which attend mainly to the previous token (e.g. head `0.7`)
* `current_token_heads`, which attend mainly to the current token (e.g. head `1.6`)
* `first_token_heads`, which attend mainly to the first token (e.g. heads `0.3` or `1.4`, although these are a bit less clear-cut than the other two)

The `prev_token_heads` and `current_token_heads` are perhaps unsurprising, because words that are close together in a sequence probably have a lot more mutual information (i.e. we could get quite far using bigram or trigram prediction). 

The `first_token_heads` are a bit more surprising. The basic intuition here is that the first token in a sequence is often used as a resting or null position for heads that only sometimes activate (since our attention probabilities always have to add up to 1).
</details>


Now that we've observed our three basic attention patterns, it's time to make detectors for those patterns!


### Exercise - write your own detectors

```c
Difficulty: 🟠🟠⚪⚪⚪
Importance: 🟠🟠🟠⚪⚪

You shouldn't spend more than 15-20 minutes on these exercises.

These exercises shouldn't be too challenging, if you understand attention patterns. Use the hint if stuck on things like how to correctly index your tensors, or how to access the activation patterns from the cache.
```

You should fill in the functions below, which act as detectors for particular types of heads. Validate your detectors by comparing these results to the visual attention patterns above - summary statistics on their own can be dodgy, but are much more reliable if you can validate it by directly playing with the data.

Tasks like this are useful, because we need to be able to take our observations / intuitions about what a model is doing, and translate these into quantitative measures. As the exercises proceed, we'll be creating some much more interesting tools and detectors!

Note - there's no objectively correct answer for which heads are doing which tasks, and which detectors can spot them. You should just try and come up with something plausible-seeming, which identifies the kind of behaviour you're looking for.


```python
def current_attn_detector(cache: ActivationCache) -> List[str]:
    '''
    Returns a list e.g. ["0.2", "1.4", "1.9"] of "layer.head" which you judge to be current-token heads
    '''
    pass

def prev_attn_detector(cache: ActivationCache) -> List[str]:
    '''
    Returns a list e.g. ["0.2", "1.4", "1.9"] of "layer.head" which you judge to be prev-token heads
    '''
    pass

def first_attn_detector(cache: ActivationCache) -> List[str]:
    '''
    Returns a list e.g. ["0.2", "1.4", "1.9"] of "layer.head" which you judge to be first-token heads
    '''
    pass


if MAIN:
    print("Heads attending to current token  = ", ", ".join(current_attn_detector(cache)))
    print("Heads attending to previous token = ", ", ".join(prev_attn_detector(cache)))
    print("Heads attending to first token    = ", ", ".join(first_attn_detector(cache)))

```

<details>
<summary>Hint</summary>

Try and compute the average attention probability along the relevant tokens. For instance, you can get the tokens just below the diagonal by using `t.diagonal` with appropriate `offset` parameter:

```python
>>> arr = t.arange(9).reshape(3, 3)
>>> arr
tensor([[0, 1, 2],
        [3, 4, 5],
        [6, 7, 8]])

>>> arr.diagonal()
tensor([0, 4, 8])

>>> arr.diagonal(-1)
tensor([3, 7])
```

Remember that you should be using `cache["pattern", layer]` to get all the attention probabilities for a given layer, and then indexing on the 0th dimension to get the correct head.
</details>

<details>
<summary>Solution </code></summary>

```python
def current_attn_detector(cache: ActivationCache) -> List[str]:
    '''
    Returns a list e.g. ["0.2", "1.4", "1.9"] of "layer.head" which you judge to be current-token heads
    '''
    attn_heads = []
    for layer in range(model.cfg.n_layers):
        for head in range(model.cfg.n_heads):
            attention_pattern = cache["pattern", layer][head]
            # take avg of diagonal elements
            score = attention_pattern.diagonal().mean()
            if score > 0.4:
                attn_heads.append(f"{layer}.{head}")
    return attn_heads

def prev_attn_detector(cache: ActivationCache) -> List[str]:
    '''
    Returns a list e.g. ["0.2", "1.4", "1.9"] of "layer.head" which you judge to be prev-token heads
    '''
    attn_heads = []
    for layer in range(model.cfg.n_layers):
        for head in range(model.cfg.n_heads):
            attention_pattern = cache["pattern", layer][head]
            # take avg of sub-diagonal elements
            score = attention_pattern.diagonal(-1).mean()
            if score > 0.4:
                attn_heads.append(f"{layer}.{head}")
    return attn_heads

def first_attn_detector(cache: ActivationCache) -> List[str]:
    '''
    Returns a list e.g. ["0.2", "1.4", "1.9"] of "layer.head" which you judge to be first-token heads
    '''
    attn_heads = []
    for layer in range(model.cfg.n_layers):
        for head in range(model.cfg.n_heads):
            attention_pattern = cache["pattern", layer][head]
            # take avg of 0th elements
            score = attention_pattern[:, 0].mean()
            if score > 0.4:
                attn_heads.append(f"{layer}.{head}")
    return attn_heads
```

Note - choosing `0.4` as a threshold is a bit arbitrary, but it seems to work well enough. In this particular case, a threshold of `0.5` results in no head being classified as a current-token head.
</details>


Compare the printouts to your attention visualisations above. Do they seem to make sense?

### Bonus - try different text

Try inputting different text, and see how stable your results are. Do you always get the same classifications for heads?


Now, it's time to turn our attention to induction heads.

## What are induction heads?

(Note: I use induction **head** to refer to the head in the second layer which attends to the 'token immediately after the copy of the current token', and induction **circuit** to refer to the circuit consisting of the composition of a **previous token head** in layer 0 and an **induction head** in layer 1)

[Induction heads](https://transformer-circuits.pub/2021/framework/index.html#induction-heads) are the first sophisticated circuit we see in transformers! And are sufficiently interesting that we wrote [another paper just about them](https://transformer-circuits.pub/2022/in-context-learning-and-induction-heads/index.html).

<details>
<summary>An aside on why induction heads are a big deal</summary>

There's a few particularly striking things about induction heads:

* They develop fairly suddenly in a phase change - from about 2B to 4B tokens we go from no induction heads to pretty well developed ones. This is a striking divergence from a 1L model [see the training curves for this model vs a 1L one](https://wandb.ai/mechanistic-interpretability/attn-only/reports/loss_ewma-22-08-24-11-08-65---VmlldzoyNTI0MDQx?accessToken=extt248d3qoxbqw1zy05kplylztjmx2uqaui3ctqb0zruem0tkpwrssq2ao1su3j) and can be observed in much larger models (eg a 13B one)
    * Phase changes are particularly interesting (and depressing) from an alignment perspective, because the prospect of a sharp left turn, or emergent capabilities like deception or situational awareness seems like worlds where alignment may be harder, and we get caught by surprise without warning shots or simpler but analogous models to test our techniques on.
* They are responsible for a significant loss decrease - so much so that there's a visible bump in the loss curve when they develop (this change in loss can be pretty comparable to the increase in loss from major increases in model size, though this is hard to make an apples-to-apples comparison)
* They seem to be responsible for the vast majority of in-context learning - the ability to use far back tokens in the context to predict the next token. This is a significant way in which transformers outperform older architectures like RNNs or LSTMs, and induction heads seem to be a big part of this.
* The same core circuit seems to be used in a bunch of more sophisticated settings, such as translation or few-shot learning - there are heads that seem clearly responsible for those *and* which double as induction heads.

</details>

Again, you are strongly recommended to read the [corresponding section of the glossary](https://dynalist.io/d/n2ZWtnoYHrU1s4vnFSAQ519J#z=_Jzi6YHRHKP1JziwdE02qdYZ), before continuing (or [this LessWrong post](https://www.lesswrong.com/posts/TvrfY4c9eaGLeyDkE/induction-heads-illustrated)). In brief, however, the induction circuit consists of a previous token head in layer 0 and an induction head in layer 1, where the induction head learns to attend to the token immediately *after* copies of the current token via K-Composition with the previous token head.

##### Question - why couldn't an induction head form in a 1L model?

<details>
<summary>Answer</summary>

Because this would require a head which attends a key position based on the *value of the token before it*. Attention scores are just a function of the key token and the query token, and are not a function of other tokens.

(The attention pattern *does* in fact include effects from other tokens because of softmax - if another key token has a high attention score, softmax inhibits this pair. But this inhibition is symmetric across positions, so can't systematically favour the token *next* to the relevant one.)

Note that a key detail is that the value of adjacent tokens are (approximately) unrelated - if the model wanted to attend based on relative *position* this is easy.
</details>


## Checking for the induction capability

A striking thing about models with induction heads is that, given a repeated sequence of random tokens, they can predict the repeated half of the sequence. This is nothing like it's training data, so this is kind of wild! The ability to predict this kind of out of distribution generalisation is a strong point of evidence that you've really understood a circuit.

To check that this model has induction heads, we're going to run it on exactly that, and compare performance on the two halves - you should see a striking difference in the per token losses.

Note - we're using small sequences (and just one sequence), since the results are very obvious and this makes it easier to visualise. In practice we'd obviously use larger ones on more subtle tasks. But it's often easiest to iterate and debug on small tasks.


### Exercise - plot per-token loss on repeated sequence

```c
Difficulty: 🟠🟠⚪⚪⚪
Importance: 🟠🟠⚪⚪⚪

You shouldn't spend more than 10-15 minutes on these exercises.
```

You should fill in the functions below. We've given you the first line of the first function, which defines a prefix (remember we need the BOS token for GPT-2, since it was trained to have one).


```python
def generate_repeated_tokens(
    model: HookedTransformer, seq_len: int, batch: int = 1
) -> Int[Tensor, "batch full_seq_len"]:
    '''
    Generates a sequence of repeated random tokens

    Outputs are:
        rep_tokens: [batch, 1+2*seq_len]
    '''
    prefix = (t.ones(batch, 1) * model.tokenizer.bos_token_id).long()
    pass

def run_and_cache_model_repeated_tokens(model: HookedTransformer, seq_len: int, batch: int = 1) -> Tuple[t.Tensor, t.Tensor, ActivationCache]:
    '''
    Generates a sequence of repeated random tokens, and runs the model on it, returning logits, tokens and cache

    Should use the `generate_repeated_tokens` function above

    Outputs are:
        rep_tokens: [batch, 1+2*seq_len]
        rep_logits: [batch, 1+2*seq_len, d_vocab]
        rep_cache: The cache of the model run on rep_tokens
    '''
    pass


if MAIN:
    seq_len = 50
    batch = 1
    (rep_tokens, rep_logits, rep_cache) = run_and_cache_model_repeated_tokens(model, seq_len, batch)
    rep_cache.remove_batch_dim()
    rep_str = model.to_str_tokens(rep_tokens)
    model.reset_hooks()
    log_probs = get_log_probs(rep_logits, rep_tokens).squeeze()
    
    print(f"Performance on the first half: {log_probs[:seq_len].mean():.3f}")
    print(f"Performance on the second half: {log_probs[seq_len:].mean():.3f}")
    
    plot_loss_difference(log_probs, rep_str, seq_len)

```

<details>
<summary>Hint</summary>

You can define the first half of the repeated tokens using `t.randint(low, high, shape)`. Also remember to specify `dtype=t.long`.

Then you can concatenate together your prefix and two copies of the repeated tokens, using `t.concat`.
</details>


<details>
<summary>Solution</summary>


```python
def generate_repeated_tokens(
    model: HookedTransformer, seq_len: int, batch: int = 1
) -> Int[Tensor, "batch full_seq_len"]:
    '''
    Generates a sequence of repeated random tokens

    Outputs are:
        rep_tokens: [batch, 1+2*seq_len]
    '''
    prefix = (t.ones(batch, 1) * model.tokenizer.bos_token_id).long()
    # SOLUTION
    rep_tokens_half = t.randint(0, model.cfg.d_vocab, (batch, seq_len), dtype=t.int64)
    rep_tokens = t.cat([prefix, rep_tokens_half, rep_tokens_half], dim=-1).to(device)
    return rep_tokens

def run_and_cache_model_repeated_tokens(model: HookedTransformer, seq_len: int, batch: int = 1) -> Tuple[t.Tensor, t.Tensor, ActivationCache]:
    '''
    Generates a sequence of repeated random tokens, and runs the model on it, returning logits, tokens and cache

    Should use the `generate_repeated_tokens` function above

    Outputs are:
        rep_tokens: [batch, 1+2*seq_len]
        rep_logits: [batch, 1+2*seq_len, d_vocab]
        rep_cache: The cache of the model run on rep_tokens
    '''
    # SOLUTION
    rep_tokens = generate_repeated_tokens(model, seq_len, batch)
    rep_logits, rep_cache = model.run_with_cache(rep_tokens)
    return rep_tokens, rep_logits, rep_cache
```
</details>


### Looking for Induction Attention Patterns

The next natural thing to check for is the induction attention pattern.

First, go back to the attention patterns visualisation code from earlier (i.e. `cv.attention.attention_heads` or `attention_patterns`) and manually check for likely heads in the second layer. Which ones do you think might be serving as induction heads?

Note - above, we defined the `rep_str` object for you, so you can use it in your `circuitsvis` functions.


```python
# YOUR CODE HERE - display the attention patterns stored in `rep_cache`, for each layer

```

<details>
<summary>What you should see (only click after you've made your own observations):</summary>

```python
for layer in range(model.cfg.n_layers):
    attention_pattern = rep_cache["pattern", layer]
    display(cv.attention.attention_patterns(tokens=rep_str, attention=attention_pattern))
```

The characteristic pattern of attention heads is a diagonal stripe, with the diagonal offset as `seq_len - 1` (because the destination token attends to the token *after* the destimation token's previous occurrence).

You should see that heads 4 and 10 are strongly induction-y, and the rest aren't.

</details>


### Exercise - make an induction-head detector

```c
Difficulty: 🟠🟠⚪⚪⚪
Importance: 🟠🟠⚪⚪⚪

You shouldn't spend more than 5-10 minutes on this exercise.

This exercise should be very similar to the earlier detector exercises (with a slightly more difficult form of indexing)
```


Now, you should make an induction pattern score function, which looks for the average attention paid to the offset diagonal. Do this in the same style as our earlier head scorers.


```python
def induction_attn_detector(cache: ActivationCache) -> List[str]:
    '''
    Returns a list e.g. ["0.2", "1.4", "1.9"] of "layer.head" which you judge to be induction heads

    Remember - the tokens used to generate rep_cache are (bos_token, *rand_tokens, *rand_tokens)
    '''
    pass


if MAIN:
    print("Induction heads = ", ", ".join(induction_attn_detector(rep_cache)))

```

If this function works as expected, then you should see output that matches your observations from `circuitsvis` (i.e. the heads which you observed to be induction heads are being classified as induction heads by your function here).

<details>
<summary>Help - I'm not sure what offset to use.</summary>

The offset in your diagonal should be `- (seq_len - 1)` (where `seq_len` is the length of the random tokens which you repeat twice), because the second instance of random token `T` will attend to the token **after** the first instance of `T`.
</details>

<details>
<summary>Solution</summary>


```python
def induction_attn_detector(cache: ActivationCache) -> List[str]:
    '''
    Returns a list e.g. ["0.2", "1.4", "1.9"] of "layer.head" which you judge to be induction heads

    Remember - the tokens used to generate rep_cache are (bos_token, *rand_tokens, *rand_tokens)
    '''
    # SOLUTION
    attn_heads = []
    for layer in range(model.cfg.n_layers):
        for head in range(model.cfg.n_heads):
            attention_pattern = cache["pattern", layer][head]
            # take avg of (-seq_len+1)-offset elements
            seq_len = (attention_pattern.shape[-1] - 1) // 2
            score = attention_pattern.diagonal(-seq_len+1).mean()
            if score > 0.4:
                attn_heads.append(f"{layer}.{head}")
    return attn_heads
```
</details>




""", unsafe_allow_html=True)


def section_3():

    st.sidebar.markdown(r"""

## Table of Contents

<ul class="contents">
    <li class='margtop'><a class='contents-el' href='#what-are-hooks'>What are hooks?</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#hook-functions'>Hook functions</a></li>
        <li><a class='contents-el' href='#running-with-hooks'>Running with hooks</a></li>
        <li><a class='contents-el' href='#a-bit-more-about-hooks'>A bit more about hooks</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#hooks:-accessing-activations'>Hooks: Accessing Activations</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#exercise-calculate-induction-scores-with-hooks'><b>Exercise</b> - calculate induction scores with hooks</a></li>
        <li><a class='contents-el' href='#exercise-find-induction-heads-in-gpt10-small'><b>Exercise</b> - find induction heads in GPT2-small</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#building-interpretability-tools'>Building interpretability tools</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#direct-logit-attribution'>Direct Logit attribution</a></li>
        <li><a class='contents-el' href='#exercise-build-logit-attribution-tool'><b>Exercise</b> - build logit attribution tool</a></li>
        <li><a class='contents-el' href='#exercise-logit-attribution-for-the-induction-heads'><b>Exercise</b> - logit attribution for the induction heads</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#hooks:-intervening-on-activations'>Hooks: Intervening on Activations</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#ablations'>Ablations</a></li>
        <li><a class='contents-el' href='#exercise-induction-head-ablation'><b>Exercise</b> - induction head ablation</a></li>
        <li><a class='contents-el' href='#bonus-different-ablations'>Bonus - different ablations</a></li>
</ul></li>""", unsafe_allow_html=True)

    st.markdown(r"""

# 3️⃣ TransformerLens: Hooks


> ##### Learning objectives
> 
> - Understand what hooks are, and how they are used in TransformerLens
> - Use hooks to access activations, process the results, and write them to an external tensor
> - Build tools to perform attribution, i.e. detecting which components of your model are responsible for performance on a given task
> - Understand how hooks can be used to perform basic interventions like **ablation**


## What are hooks?

One of the great things about interpreting neural networks is that we have *full control* over our system. From a computational perspective, we know exactly what operations are going on inside (even if we don't know what they mean!). And we can make precise, surgical edits and see how the model's behaviour and other internals change. This is an extremely powerful tool, because it can let us e.g. set up careful counterfactuals and causal intervention to easily understand model behaviour. 

Accordingly, being able to do this is a pretty core operation, and this is one of the main things TransformerLens supports! The key feature here is **hook points**. Every activation inside the transformer is surrounded by a hook point, which allows us to edit or intervene on it. 

We do this by adding a **hook function** to that activation, and then calling `model.run_with_hooks`.

*(Terminology note - because basically all the activations in our model have an associated hook point, we'll sometimes use the terms "hook" and "activation" interchangeably.)*


### Hook functions

Hook functions take two arguments: `activation_value` and `hook_point`. The `activation_value` is a tensor representing some activation in the model, just like the values in our `ActivationCache`. The `hook_point` is an object which gives us methods like `hook.layer()` or attributes like `hook.name` that are sometimes useful to call within the function.

If we're using hooks to edit activations, then the hook function should return a tensor of the same shape as the activation value. But we can also just have our hook function access the activation, do some processing, and write the results to some external variable (in which case our hook function should just not return anything).

An example hook function for changing the attention patterns at a particular layer might look like:


```python
def hook_function(
    attn_pattern: Float[Tensor, "batch heads seqQ seqK"],
    hook: HookPoint
) -> Float[Tensor, "batch heads seqQ seqK"]:

    # modify attn_pattern (can be inplace)
    return attn_pattern
```


### Running with hooks

Once you've defined a hook function (or functions), you should call `model.run_with_hooks`. A typical call to this function might look like:




```python
loss = model.run_with_hooks(
    tokens, 
    return_type="loss",
    fwd_hooks=[
        ('blocks.1.attn.hook_pattern', hook_function)
    ]
)
```


Let's break this code down.

* `tokens` represents our model's input.
* `return_type="loss"` is used here because we're modifying our activations and seeing how this affects the loss.
    * We could also return the logits, or just use `return_type=None` if we only want to access the intermediate activations and we don't care about the output.
* `fwd_hooks` is a list of 2-tuples of (hook name, hook function).
    * The hook name is a string that specifies which activation we want to hook. 
    * The hook function gets run with the corresponding activation as its first argument.

### A bit more about hooks

Here are a few extra notes for how to squeeze even more functionality out of hooks. If you'd prefer, you can [jump ahead](#hooks-accessing-activations) to see an actual example of hooks being used, and come back to this section later.

<details>
<summary>Resetting hooks</summary>

`model.run_with_hooks` has the default parameter `reset_hooks_end=True` which resets all hooks at the end of the run (including both those that were added before and during the run).

Despite this, it's possible to shoot yourself in the foot with hooks, e.g. if there's an error in one of your hooks so the function never finishes. In this case, you can use `model.reset_hooks()` to reset all hooks.

Further, if you *do* want to keep the hooks that you add, you can do this by calling `add_hook` on the relevant `HookPoint`.
</details>
<details>
<summary>Adding multiple hooks at once</summary>

Including more than one tuple in the `fwd_hooks` list is one way to add multiple hooks:

```python
loss = model.run_with_hooks(
    tokens, 
    return_type="loss",
    fwd_hooks=[
        ('blocks.0.attn.hook_pattern', hook_function),
        ('blocks.1.attn.hook_pattern', hook_function)
    ]
)
```

Another way is to use a **name filter** rather than a single name:

```python
loss = model.run_with_hooks(
    tokens,
    return_type="loss",
    fwd_hooks=[
        (lambda name: name.endswith("pattern"), hook_function)
    ]
)
```
</details>
<details>
<summary><code>utils.get_act_name</code></summary>

When we were indexing the cache in the previous section, we found we could use strings like `cache['blocks.0.attn.hook_pattern']`, or use the shorthand of `cache['pattern', 0]`. The reason the second one works is that it calls the function `utils.get_act_name` under the hood, i.e. we have:

```python
utils.get_act_name('pattern', 0) == 'blocks.0.attn.hook_pattern'
```

Using `utils.get_act_name` in your forward hooks is often easier than using the full string, since the only thing you need to remember is the activation name (you can refer back to the diagram in the previous section for this).
</details>
<details>
<summary>Using <code>functools.partial</code> to create variations on hooks</summary>

A useful trick is to define a hook function with more arguments than it needs, and then use `functools.partial` to fill in the extra arguments. For instance, if you want a hook function which only modifies a particular head, but you want to run it on all heads separately (rather than just adding all the hooks and having them all run on the next forward pass), then you can do something like:

```python
def hook_all_attention_patterns(
    attn_pattern: Float[Tensor, "batch heads seqQ seqK"],
    hook: HookPoint,
    head_idx: int
) -> Float[Tensor, "batch heads seqQ seqK"]:
    # modify attn_pattern inplace, at head_idx
    return attn_pattern

for head_idx in range(12):
    temp_hook_fn = functools.partial(hook_all_attention_patterns, head_idx=head_idx)
    model.run_with_hooks(tokens, fwd_hooks=[('blocks.1.attn.hook_pattern', temp_hook_fn)])
```
</details>

And here are some points of interest, which aren't vital to understand:

<details>
<summary>Relationship to PyTorch hooks</summary>

[PyTorch hooks](https://blog.paperspace.com/pytorch-hooks-gradient-clipping-debugging/) are a great and underrated, yet incredibly janky, feature. They can act on a layer, and edit the input or output of that layer, or the gradient when applying autodiff. The key difference is that **Hook points** act on *activations* not layers. This means that you can intervene within a layer on each activation, and don't need to care about the precise layer structure of the transformer. And it's immediately clear exactly how the hook's effect is applied. This adjustment was shamelessly inspired by [Garcon's use of ProbePoints](https://transformer-circuits.pub/2021/garcon/index.html).

They also come with a range of other quality of life improvements. PyTorch's hooks are global state, which can be a massive pain if you accidentally leave a hook on a model. TransformerLens hooks are also global state, but `run_with_hooks` tries tries to create an abstraction where these are local state by removing all hooks at the end of the function (and they come with a helpful `model.reset_hooks()` method to remove all hooks).
</details>

<details>
<summary>How are TransformerLens hooks actually implemented?</summary>

They are implemented as `nn.Identity` modules with special features for adding and removing hook functions (this is why you see hooks when you print a HookedTransformer model, because all its modules are recursively printed).

When you run the model normally, hook modules won't change the model's behaviour (since applying the identity function does nothing). It's only once you add functions to the hook modules (e.g. a function which ablates any inputs into the hook module) that the model's behaviour changes.
</details>


## Hooks: Accessing Activations

In later sections, we'll write some code to intervene on hooks, which is really the core feature that makes them so useful for interpretability. But for now, let's just look at how to access them without changing their value. This can be achieved by having the hook function write to a global variable, and return nothing (rather than modifying the activation in place).

Why might we want to do this? It turns out to be useful for things like:

* Extracting activations for a specific task
* Doing some long-running calculation across many inputs, e.g. finding the text that most activates a specific neuron

Note that, in theory, this could all be done using the `run_with_cache` function we used in the previous section, combined with post-processing of the cache result. But using hooks can be more intuitive and memory efficient.


### Exercise - calculate induction scores with hooks

```c
Difficulty: 🟠🟠🟠⚪⚪
Importance: 🟠🟠🟠🟠⚪

You shouldn't spend more than 15-20 minutes on this exercise.

This is our first exercise with hooks, which are an absolutely vital TransformerLens tool. Use the hints if you're stuck.
```

To start with, we'll look at how hooks can be used to get the same results as from the previous section (where we ran our induction head detector functions on the values in the cache).

Most of the code has already been provided for you below; the only thing you need to do is **implement the `induction_score_hook` function**. As mentioned, this function takes two arguments: the activation value (which in this case will be our attention pattern) and the hook object (which gives us some useful methods and attributes that we can access in the function, e.g. `hook.layer()` to return the layer, or `hook.name` to return the name, which is the same as the name in the cache). 

Your function should do the following:

* Calculate the induction score for the attention pattern `pattern`, using the same methodology as you used in the previous section when you wrote your induction head detectors.
    * Note that this time, the batch dimension is greater than 1, so you should compute the average attention score over the batch dimension.
    * Also note that you are computing the induction score for all heads at once, rather than one at a time. You might find the arguments `dim1` and `dim2` of the `torch.diagonal` function useful.
* Write this score to the tensor `induction_score_store`, which is a global variable that we've provided for you. The `[i, j]`th element of this tensor should be the induction score for the `j`th head in the `i`th layer.


```python

if MAIN:
    seq_len = 50
    batch = 10
    rep_tokens_10 = generate_repeated_tokens(model, seq_len, batch)
    
    # We make a tensor to store the induction score for each head.
    # We put it on the model's device to avoid needing to move things between the GPU and CPU, which can be slow.
    induction_score_store = t.zeros((model.cfg.n_layers, model.cfg.n_heads), device=model.cfg.device)
    
def induction_score_hook(
    pattern: Float[Tensor, "batch head_index dest_pos source_pos"],
    hook: HookPoint,
):
    '''
    Calculates the induction score, and stores it in the [layer, head] position of the `induction_score_store` tensor.
    '''
    pass


if MAIN:
    pattern_hook_names_filter = lambda name: name.endswith("pattern")
    
    # Run with hooks (this is where we write to the `induction_score_store` tensor`)
    model.run_with_hooks(
        rep_tokens_10, 
        return_type=None, # For efficiency, we don't need to calculate the logits
        fwd_hooks=[(
            pattern_hook_names_filter,
            induction_score_hook
        )]
    )
    
    # Plot the induction scores for each head in each layer
    imshow(
        induction_score_store, 
        labels={"x": "Head", "y": "Layer"}, 
        title="Induction Score by Head", 
        text_auto=".2f",
        width=900, height=400
    )

```

If this function has been implemented correctly, you should see a result matching your observations from the previous section: a high induction score (close to 1) for all the heads which you identified as induction heads, and a low score (close to 0) for all others.

<details>
<summary>Help - I'm not sure how to implement this function.</summary>

To get the induction stripe, you can use:

```python
torch.diagonal(pattern, dim1=-2, dim2=-1, offset=1-seq_len)
```

since this returns the diagonal of each attention scores matrix, for every element in the batch and every attention head.

Once you have this, you can then take the mean over the batch and diagonal dimensions, giving you a tensor of length `n_heads`. You can then write this to the global `induction_score_store` tensor, using the `hook.layer()` method to get the correct row number.
</details>

<details>
<summary>Solution</summary>


```python
def induction_score_hook(
    pattern: Float[Tensor, "batch head_index dest_pos source_pos"],
    hook: HookPoint,
):
    '''
    Calculates the induction score, and stores it in the [layer, head] position of the `induction_score_store` tensor.
    '''
    # SOLUTION
    # Take the diagonal of attn paid from each dest posn to src posns (seq_len-1) tokens back
    # (This only has entries for tokens with index>=seq_len)
    induction_stripe = pattern.diagonal(dim1=-2, dim2=-1, offset=1-seq_len)
    # Get an average score per head
    induction_score = einops.reduce(induction_stripe, "batch head_index position -> head_index", "mean")
    # Store the result.
    induction_score_store[hook.layer(), :] = induction_score

# We make a boolean filter on activation names, that's true only on attention pattern names
```
</details>


### Exercise - find induction heads in GPT2-small

```c
Difficulty: 🟠🟠🟠⚪⚪
Importance: 🟠🟠🟠🟠⚪

You shouldn't spend more than 10-20 minutes on this exercise.

Here, you mostly just need to use previously defined functions and interpret the results, rather than writing new code.
```

*This is your first opportunity to investigate a larger and more extensively trained model, rather than the simple 2-layer model we've been using so far. None of the code required is new (you can copy most of it from previous sections), so these exercises shouldn't take very long.*


Perform the same analysis on your `gpt2_small`. You should observe that some heads, particularly in a couple of the middle layers, have high induction scores. Use CircuitsVis to plot the attention patterns for these heads when run on the repeated token sequences, and verify that they look like induction heads.

Note - you can make CircuitsVis plots (and other visualisations) using hooks rather than plotting directly from the cache. For example, we've given you a hook function which will display the attention patterns at a given hook when you include it in a call to `model.run_with_hooks`.


```python
def visualize_pattern_hook(
    pattern: Float[Tensor, "batch head_index dest_pos source_pos"],
    hook: HookPoint,
):
    print("Layer: ", hook.layer())
    display(
        cv.attention.attention_patterns(
            tokens=gpt2_small.to_str_tokens(rep_tokens[0]), 
            attention=pattern.mean(0)
        )
    )


if MAIN:
    # YOUR CODE HERE - find induction heads in gpt2_small

```

<details>
<summary>Solution </summary>

```python
seq_len = 50
batch = 10
rep_tokens_10 = generate_repeated_tokens(gpt2_small, seq_len, batch)

induction_score_store = t.zeros((gpt2_small.cfg.n_layers, gpt2_small.cfg.n_heads), device=gpt2_small.cfg.device)

gpt2_small.run_with_hooks(
    rep_tokens_10, 
    return_type=None, # For efficiency, we don't need to calculate the logits
    fwd_hooks=[(
        pattern_hook_names_filter,
        induction_score_hook
    )]
)

imshow(
    induction_score_store, 
    labels={"x": "Head", "y": "Layer"},
    title="Induction Score by Head", 
    text_auto=".1f",
    width=800
)

# Observation: heads 5.1, 5.5, 6.9, 7.2, 7.10 are all strongly induction-y.
# Confirm observation by visualizing attn patterns for layers 5 through 7:

for induction_head_layer in [5, 6, 7]:
    gpt2_small.run_with_hooks(
        rep_tokens, 
        return_type=None, # For efficiency, we don't need to calculate the logits
        fwd_hooks=[
            (utils.get_act_name("pattern", induction_head_layer), visualize_pattern_hook)
        ]
    )
```
</details>


## Building interpretability tools

In order to develop a mechanistic understanding for how transformers perform certain tasks, we need to be able to answer questions like:

> *How much of the model's performance on some particular task is attributable to each component of the model?*

where "component" here might mean, for example, a specific head in a layer.

There are many ways to approach a question like this. For example, we might look at how a head interacts with other heads in different layers, or we might perform a causal intervention by seeing how well the model performs if we remove the effect of this head. However, we'll keep things simple for now, and ask the question: **what are the direct contributions of this head to the output logits?**

### Direct Logit attribution

A consequence of the residual stream is that the output logits are the sum of the contributions of each layer, and thus the sum of the results of each head. This means we can decompose the output logits into a term coming from each head and directly do attribution like this!

<details>
<summary>A concrete example</summary>

Let's say that our model knows that the token Harry is followed by the token Potter, and we want to figure out how it does this. The logits on Harry are `residual @ W_U`. But this is a linear map, and the residual stream is the sum of all previous layers `residual = embed + attn_out_0 + attn_out_1`. So `logits = (embed @ W_U) + (attn_out @ W_U) + (attn_out_1 @ W_U)`

We can be even more specific, and *just* look at the logit of the Potter token - this corresponds to a row of `W_U`, and so a direction in the residual stream - our logit is now a single number that is the sum of `(embed @ potter_U) + (attn_out_0 @ potter_U) + (attn_out_1 @ potter_U)`. Even better, we can decompose each attention layer output into the sum of the result of each head, and use this to get many terms.
</details>

Your mission here is to write a function to look at how much each component contributes to the correct logit. Your components are:

* The direct path (i.e. the residual connections from the embedding to unembedding),
* Each layer 0 head (via the residual connection and skipping layer 1)
* Each layer 1 head

To emphasise, these are not paths from the start to the end of the model, these are paths from the output of some component directly to the logits - we make no assumptions about how each path was calculated!

A few important notes for this exercise:

* Here we are just looking at the DIRECT effect on the logits, i.e. the thing that this component writes / embeds into the residual stream - if heads compose with other heads and affect logits like that, or inhibit logits for other tokens to boost the correct one we will not pick up on this!
* By looking at just the logits corresponding to the correct token, our data is much lower dimensional because we can ignore all other tokens other than the correct next one (Dealing with a 50K vocab size is a pain!). But this comes at the cost of missing out on more subtle effects, like a head suppressing other plausible logits, to increase the log prob of the correct one.
    * There are other situations where our job might be easier. For instance, in the IOI task (which we'll discuss shortly) we're just comparing the logits of the indirect object to the logits of the direct object, meaning we can use the **difference between these logits**, and ignore all the other logits.
* When calculating correct output logits, we will get tensors with a dimension `(position - 1,)`, not `(position,)` - we remove the final element of the output (logits), and the first element of labels (tokens). This is because we're predicting the *next* token, and we don't know the token after the final token, so we ignore it.

<details>
<summary>Aside - centering <code>W_U</code></summary>

While we won't worry about this for this exercise, logit attribution is often more meaningful if we first center `W_U` - i.e. ensure the mean of each row writing to the output logits is zero. Log softmax is invariant when we add a constant to all the logits, so we want to control for a head that just increases all logits by the same amount. We won't do this here for ease of testing.
</details>

<details>
<summary>Question - why don't we do this to the log probs instead?</summary>

Because log probs aren't linear, they go through `log_softmax`, a non-linear function.
</details>


### Exercise - build logit attribution tool

```c
Difficulty: 🟠🟠🟠⚪⚪
Importance: 🟠🟠🟠🟠⚪

You shouldn't spend more than 10-15 minutes on this exercise.

This exercise is important, but has quite a few messy einsums, so you might get more value from reading the solution than doing the exercises.
```

You should implement the `logit_attribution` function below. This should return the contribution of each component in the "correct direction". We've already given you the unembedding vectors for the correct direction, `W_U_correct_tokens` (note that we take the `[1:]` slice of tokens, for reasons discussed above).

The code below this function will check your logit attribution function is working correctly, by taking the sum of logit attributions and comparing it to the actual values in the residual stream at the end of your model.


```python
def logit_attribution(
    embed: Float[Tensor, "seq d_model"],
    l1_results: Float[Tensor, "seq nheads d_model"],
    l2_results: Float[Tensor, "seq nheads d_model"],
    W_U: Float[Tensor, "d_model d_vocab"],
    tokens: Int[Tensor, "seq"]
) -> Float[Tensor, "seq-1 n_components"]:
    '''
    Inputs:
        embed: the embeddings of the tokens (i.e. token + position embeddings)
        l1_results: the outputs of the attention heads at layer 1 (with head as one of the dimensions)
        l2_results: the outputs of the attention heads at layer 2 (with head as one of the dimensions)
        W_U: the unembedding matrix
        tokens: the token ids of the sequence

    Returns:
        Tensor of shape (seq_len-1, n_components)
        represents the concatenation (along dim=-1) of logit attributions from:
            the direct path (seq-1,1)
            layer 0 logits (seq-1, n_heads)
            layer 1 logits (seq-1, n_heads)
        so n_components = 1 + 2*n_heads
    '''
    W_U_correct_tokens = W_U[:, tokens[1:]]
    pass


if MAIN:
    text = "We think that powerful, significantly superhuman machine intelligence is more likely than not to be created this century. If current machine learning techniques were scaled up to this level, we think they would by default produce systems that are deceptive or manipulative, and that no solid plans are known for how to avoid this."
    logits, cache = model.run_with_cache(text, remove_batch_dim=True)
    str_tokens = model.to_str_tokens(text)
    tokens = model.to_tokens(text)
    
    with t.inference_mode():
        embed = cache["embed"]
        l1_results = cache["result", 0]
        l2_results = cache["result", 1]
        logit_attr = logit_attribution(embed, l1_results, l2_results, model.W_U, tokens[0])
        # Uses fancy indexing to get a len(tokens[0])-1 length tensor, where the kth entry is the predicted logit for the correct k+1th token
        correct_token_logits = logits[0, t.arange(len(tokens[0]) - 1), tokens[0, 1:]]
        t.testing.assert_close(logit_attr.sum(1), correct_token_logits, atol=1e-3, rtol=0)
        print("Tests passed!")

```

<details>
<summary>Solution</summary>


```python
def logit_attribution(
    embed: Float[Tensor, "seq d_model"],
    l1_results: Float[Tensor, "seq nheads d_model"],
    l2_results: Float[Tensor, "seq nheads d_model"],
    W_U: Float[Tensor, "d_model d_vocab"],
    tokens: Int[Tensor, "seq"]
) -> Float[Tensor, "seq-1 n_components"]:
    '''
    Inputs:
        embed: the embeddings of the tokens (i.e. token + position embeddings)
        l1_results: the outputs of the attention heads at layer 1 (with head as one of the dimensions)
        l2_results: the outputs of the attention heads at layer 2 (with head as one of the dimensions)
        W_U: the unembedding matrix
        tokens: the token ids of the sequence

    Returns:
        Tensor of shape (seq_len-1, n_components)
        represents the concatenation (along dim=-1) of logit attributions from:
            the direct path (seq-1,1)
            layer 0 logits (seq-1, n_heads)
            layer 1 logits (seq-1, n_heads)
        so n_components = 1 + 2*n_heads
    '''
    W_U_correct_tokens = W_U[:, tokens[1:]]
    # SOLUTION
    direct_attributions = einops.einsum(W_U_correct_tokens, embed[:-1], "emb seq, seq emb -> seq")
    l1_attributions = einops.einsum(W_U_correct_tokens, l1_results[:-1], "emb seq, seq nhead emb -> seq nhead")
    l2_attributions = einops.einsum(W_U_correct_tokens, l2_results[:-1], "emb seq, seq nhead emb -> seq nhead")
    return t.concat([direct_attributions.unsqueeze(-1), l1_attributions, l2_attributions], dim=-1)
```
</details>


Once you've got the tests working, you can visualise the logit attributions for each path through the model. We've provided you with the helper function `plot_logit_attribution`, which presents the results in a nice way.


```python

if MAIN:
    embed = cache["embed"]
    l1_results = cache["result", 0]
    l2_results = cache["result", 1]
    logit_attr = logit_attribution(embed, l1_results, l2_results, model.W_U, tokens[0])
    
    plot_logit_attribution(model, logit_attr, tokens)

```

#### Question - what is the interpretation of this plot?

You should find that the most variation in the logit attribution comes from the direct path. In particular, some of the tokens in the direct path have a very high logit attribution (e.g. tokens 12, 24 and 46). Can you guess what gives them in particular such a high logit attribution? 

<details>
<summary>Answer</summary>

The tokens with very high logit attribution are the ones which "offer very probable bigrams". For instance, the highest contribution on the direct path comes from `| manip|`, because this is very likely to be followed by `|ulative|` (or presumably a different stem like `| ulation|`). `| super|` -> `|human|` is another example of a bigram formed when the tokenizer splits one word into multiple tokens.

There are also examples that come from two different words, rather than a single word split by the tokenizer. These include:

* `| more|` -> `| likely|`
* `| machine|` -> `| learning|`
* `| by|` -> `| default|`
* `| how|` -> `| to|`

See later for a discussion of all the ~infuriating~ fun quirks of tokenization!
</details>

Another feature of the plot - the heads in the second layer seem to have much higher contributions than the heads in the first layer. Why do you think this might be?

<details>
<summary>Hint</summary>

Think about what this graph actually represents, in terms of paths through the transformer.
</details>

<details>
<summary>Answer</summary>

This is because of a point we discussed earlier - this plot doesn't pick up on things like a head's effect in composition with another head. So the attribution for layer-0 heads won't involve any composition, whereas the attributions for layer-1 heads will involve not only the single-head paths through those attention heads, but also the 2-layer compositional paths through heads in layer 0 and layer 1.
</details>


### Exercise - logit attribution for the induction heads

```c
Difficulty: 🟠🟠🟠⚪⚪
Importance: 🟠🟠⚪⚪⚪

You shouldn't spend more than ~10 minutes on this exercise.

This exercise just involves calling logit_attribution with appropriate arguments. Don't spend too long on it, you should look at solutions if you are stuck.
```

Perform logit attribution for your attention-only model `model`, on the `rep_cache`. What do you expect to see?

Remember, you'll need to split the sequence in two, with one overlapping token (since predicting the next token involves removing the final token with no label) - your `logit_attr` should both have shape `[seq_len, 2*n_heads + 1]` (ie `[50, 25]` here).

<details>
<summary>Note - the first plot will be pretty meaningless. Can you see why?</summary>

Because the first plot shows the logit attribution for the first half of the sequence, i.e. the first occurrence of each of the tokens. Since there is no structure to this sequence (it is purely random), there is no reason to expect the heads to be doing meaningful computation. The structure lies in the second half of the sequence, when the tokens are repeated, and the heads with high logit attributions will be the ones that can perform induction.
</details>


```python

if MAIN:
    seq_len = 50
    
    embed = rep_cache["embed"]
    l1_results = rep_cache["result", 0]
    l2_results = rep_cache["result", 1]
    first_half_tokens = rep_tokens[0, : 1 + seq_len]
    second_half_tokens = rep_tokens[0, seq_len:]
    
    # YOUR CODE HERE - define `first_half_logit_attr` and `second_half_logit_attr`
    assert first_half_logit_attr.shape == (seq_len, 2*model.cfg.n_heads + 1)
    assert second_half_logit_attr.shape == (seq_len, 2*model.cfg.n_heads + 1)
    
    plot_logit_attribution(model, first_half_logit_attr, first_half_tokens, "Logit attribution (first half of repeated sequence)")
    plot_logit_attribution(model, second_half_logit_attr, second_half_tokens, "Logit attribution (second half of repeated sequence)")

```

<details>
<summary>Solution</summary>


```python
# (each with a single call to the `logit_attribution` function)
first_half_logit_attr = logit_attribution(embed[:seq_len+1], l1_results[:seq_len+1], l2_results[:seq_len+1], model.W_U, first_half_tokens)
second_half_logit_attr = logit_attribution(embed[seq_len:], l1_results[seq_len:], l2_results[seq_len:], model.W_U, second_half_tokens)

```
</details>

What is the interpretation of this plot, in the context of our induction head circuit?

<details>
<summary>Answer</summary>

Previously, we observed that heads `1.4` and `1.10` seemed to be acting as induction heads.

This plot gives further evidence that this is the case, since these two heads have a large logit attribution score **on sequences in which the only way to get accurate predictions is to use the induction mechanism**.

This also agrees with our attention scores result, in showing tht `1.10` is a stronger induction head than `1.4`.
</details>


## Hooks: Intervening on Activations

Now that we've built some tools to decompose our model's output, it's time to start making causal interventions.

### Ablations

Let's start with a simple example: **ablation**. An ablation is a simple causal intervention on a model - we pick some part of it and set it to zero. This is a crude proxy for how much that part matters. Further, if we have some story about how a specific circuit in the model enables some capability, showing that ablating *other* parts does nothing can be strong evidence of this.

As mentioned in [the glossary](https://dynalist.io/d/n2ZWtnoYHrU1s4vnFSAQ519J#z=fh-HJyz1CgUVrXuoiban6bYx), there are many ways to do ablation. We'll focus on the simplest: zero-ablation (even though it's somewhat unprincipled).


### Exercise - induction head ablation

```c
Difficulty: 🟠🟠⚪⚪⚪
Importance: 🟠🟠🟠🟠⚪

You shouldn't spend more than ~10 minutes on this exercise.

This exercise is conceptually important, but very short.
```

The code below provides a template for performing zero-ablation on the value vectors at a particular head (i.e. the vectors we get when applying the weight matrices `W_V` to the residual stream). If you're confused about what different activations mean, you can refer back to [the diagram](https://mermaid.ink/svg/pako:eNrNVsFu2zAM_RVBh7UDYnQLdnKyHIasOfQwFCu2Q10EikXHhmVJkWQ3Sd1_H-U4dR2kQLFDEx0kUibtR_pR1BONFQca0qVhOiV300gSHLZc7DYiOraaSWLdRsD3i0RJF9hsC-Hwm15fTO4MkzZRpgDzQ6g4J5fMOUmUFJvP4yvvOYno7pV-xIJZO4WEQKHdhjxm3KXhF70epJAtU-fF0RFrDxEnoUxogKNFZ2PAZnyuDdxH9EUe86zaI14ow8EETulwqNfEKpFxshAszkcFM8tMNo-aYMZX6DcZN19rvbuPdpF_HXrjSwurAeHzAq0Fxuq9MNaHIAim9-QhDMMmxiCY1IzzusWmrOuwd9J7090k9xMUVo_6y7G9dyz_Nx_5sX5UfXXVV_O-6iOZ21hhXvoPrvuqRkMwsr8566vbvoqvLMWrNIPkR_jif8zf-Z-6QuJUH0cYmQLjnjd-7dNmdkCbx6YmgBNWLYlKSMVECaSC2Clj6y3i3p4eN0GkBBP5q96lfVeGKJwA2mEpemy1LQuiKjDEW9m64Z0qPc69eOrT4k1y3tYrhLk6C3JeH5CTK0e0UbyMHWFCyWXrNSA2ZgIIk5wUzOb1q0Lf53ynfUhYbUQY3W0z3_SiQnaoxBVsXbfHDCJspTNAF8zeZMZNnSPU_DyYcayhde2u68uonLLUDmFiW6ADiheXgmUcL0BPfjuiLoUCIhqiyCFhvpNgn3tG01Jz5uAnz_D8pWHChIUBZaVTvzcypqEzJeyNphnDfl60Vs__ANh9IJM).

**The only thing left for you to do is fill in the function `head_ablation_hook`** so that it performs zero-ablation on the head given by `head_index_to_ablate`. In other words, your function should return a modified version of `value` with this head ablated. (Technically you don't have to return any tensor if you're modifying `value` in-place; this is just convention.)

A few notes to help explain the code below:

* In the `get_ablation_scores` function, we run our hook function in a for loop: once for each layer and each head. Each time, we write a single value to the tensor `ablation_scores` that stores the results of ablating that particular head.
* We can get the output logits then calculate `cross_entropy_loss`, but we can also just use `return_type="loss"` which does this calculation directly. This is in contrast to the logit diff metric we used in the previous section.
    * If the head didn't have any effect on the output, then the ablation score would be zero (since the loss doesn't increase when we ablate).
    * If the head was very important for making correct predictions, then we should see a very large ablation score.
* We use `functools.partial` to create a temporary hook function with the head number fixed. This is a nice way to avoid having to write a separate hook function for each head.
* We use `utils.get_act_name` to get the name of our activation. This is a nice shorthand way of getting the full name.


```python
def head_ablation_hook(
    attn_result: Float[Tensor, "batch seq n_heads d_model"],
    hook: HookPoint,
    head_index_to_ablate: int
) -> Float[Tensor, "batch seq n_heads d_model"]:
    pass

    
def cross_entropy_loss(logits, tokens):
    '''
    Computes the mean cross entropy between logits (the model's prediction) and tokens (the true values).

    (optional, you can just use return_type="loss" instead.)
    '''
    log_probs = F.log_softmax(logits, dim=-1)
    pred_log_probs = t.gather(log_probs[:, :-1], -1, tokens[:, 1:, None])[..., 0]
    return -pred_log_probs.mean()


def get_ablation_scores(
    model: HookedTransformer, 
    tokens: Int[Tensor, "batch seq"]
) -> Float[Tensor, "n_layers n_heads"]:
    '''
    Returns a tensor of shape (n_layers, n_heads) containing the increase in cross entropy loss from ablating the output of each head.
    '''
    # Initialize an object to store the ablation scores
    ablation_scores = t.zeros((model.cfg.n_layers, model.cfg.n_heads), device=model.cfg.device)

    # Calculating loss without any ablation, to act as a baseline
    model.reset_hooks()
    logits = model(tokens, return_type="logits")
    loss_no_ablation = cross_entropy_loss(logits, tokens)

    for layer in tqdm(range(model.cfg.n_layers)):
        for head in range(model.cfg.n_heads):
            # Use functools.partial to create a temporary hook function with the head number fixed
            temp_hook_fn = functools.partial(head_ablation_hook, head_index_to_ablate=head)
            # Run the model with the ablation hook
            ablated_logits = model.run_with_hooks(tokens, fwd_hooks=[
                (utils.get_act_name("result", layer), temp_hook_fn)
            ])
            # Calculate the logit difference
            loss = cross_entropy_loss(ablated_logits, tokens)
            # Store the result, subtracting the clean loss so that a value of zero means no change in loss
            ablation_scores[layer, head] = loss - loss_no_ablation

    return ablation_scores



if MAIN:
    ablation_scores = get_ablation_scores(model, rep_tokens)
    tests.test_get_ablation_scores(ablation_scores, model, rep_tokens)

```

<details>
<summary>Solution</summary>


```python
def head_ablation_hook(
    attn_result: Float[Tensor, "batch seq n_heads d_model"],
    hook: HookPoint,
    head_index_to_ablate: int
) -> Float[Tensor, "batch seq n_heads d_model"]:
    # SOLUTION
    attn_result[:, :, head_index_to_ablate, :] = 0.0
    return attn_result
```
</details>


Once you've passed the tests, you can plot the results:



```python

if MAIN:
    imshow(
        ablation_scores, 
        labels={"x": "Head", "y": "Layer", "color": "Logit diff"},
        title="Logit Difference After Ablating Heads", 
        text_auto=".2f",
        width=900, height=400
    )

```

What is your interpretation of these results?

<details>
<summary>Interpretation</summary>

This tells us not just which heads are responsible for writing output to the residual stream that gets us the correct result, but **which heads play an important role in the induction circuit**. 

This chart tells us that - for sequences of repeated tokens - head `0.7` is by far the most important in layer 0 (which makes sense, since we observed it to be the strongest "previous token head"), and heads `1.4`, `1.10` are the most important in layer 1 (which makes sense, since we observed these to be the most induction-y).

This is a good illustration of the kind of result which we can get from ablation, but **wouldn't be able to get from something like direct logit attribution**, because it isn't a causal intervention.
</details>

### Bonus - different ablations

Try ablating *every* head apart from the previous token head and the two induction heads. What does this do to performance?

What if you mean ablate it, rather than zero ablating it?

*(In later sections e.g. Indirect Object Identification, we'll use hooks to implement some more advanced causal interventions, such as **activation patching** and **causal tracing**.)*




""", unsafe_allow_html=True)


def section_4():

    st.sidebar.markdown(r"""

## Table of Contents

<ul class="contents">
    <li class='margtop'><a class='contents-el' href='#refresher-the-induction-circuit'>Refresher - the induction circuit</a></li>
    <li class='margtop'><a class='contents-el' href='#refresher-qk-and-ov-circuits'>Refresher - QK and OV circuits</a></li>
    <li class='margtop'><a class='contents-el' href='#factored-matrix-class'>Factored Matrix class</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#exercise-deriving-properties-of-a-factored-matrix'><b>Exercise</b> - deriving properties of a factored matrix</a></li>
        <li><a class='contents-el' href='#basic-examples'>Basic Examples</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#reverse-engineering-circuits'>Reverse-engineering circuits</a></li>
    <li class='margtop'><a class='contents-el' href='#[1]-ov-copying-circuit'>[1] OV copying circuit</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#exercise-compute-ov-circuit-for-1-10'><b>Exercise</b> - compute OV circuit for <code>1.4</code></a></li>
        <li><a class='contents-el' href='#exercise-verify-this-is-the-identity'><b>Exercise</b> - verify this is the identity</a></li>
        <li><a class='contents-el' href='#exercise-compute-effective-circuit'><b>Exercise</b> - compute effective circuit</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#[10]-qk-prev-token-circuit'>[2] QK prev-token circuit</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#exercise-compute-full-qk-circuit-for-0-125'><b>Exercise</b> - compute full QK-circuit for <code>0.7</code></a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#[125]-k-composition-circuit'>[3] K-composition circuit</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#exercise-analyse-the-relative-importance'><b>Exercise</b> - analyse the relative importance</a></li>
        <li><a class='contents-el' href='#exercise-decompose-attention-scores'><b>Exercise</b> - decompose attention scores</a></li>
        <li><a class='contents-el' href='#interpreting-the-full-circuit'>Interpreting the full circuit</a></li>
        <li><a class='contents-el' href='#exercise-compute-the-k-comp-circuit'><b>Exercise</b> - compute the K-comp circuit</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#further-exploration-of-induction-circuits'>Further Exploration of Induction Circuits</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#composition-scores'>Composition scores</a></li>
        <li><a class='contents-el' href='#exercise-calculate-composition-scores'><b>Exercise</b> - calculate composition scores</a></li>
        <li><a class='contents-el' href='#exercise-setting-a-baseline'><b>Exercise</b> - Setting a Baseline</a></li>
        <li><a class='contents-el' href='#exercise-batching-and-using-the-factoredmatrix-class'><b>Exercise</b> - batching, and using the <code>FactoredMatrix</code> class</a></li>
        <li><a class='contents-el' href='#targeted-ablations'>Targeted Ablations</a></li>
    </ul></li>
    <li class='margtop'><a class='contents-el' href='#bonus'>Bonus</a></li>
    <li><ul class="contents">
        <li><a class='contents-el' href='#looking-for-circuits-in-real-llms'>Looking for Circuits in Real LLMs</a></li>
        <li><a class='contents-el' href='#training-your-own-toy-models'>Training Your Own Toy Models</a></li>
        <li><a class='contents-el' href='#interpreting-induction-heads-during-training'>Interpreting Induction Heads During Training</a></li>
        <li><a class='contents-el' href='#further-discussion-/-investigation'>Further discussion / investigation</a></li>
</ul></li>""", unsafe_allow_html=True)

    st.markdown(r"""

# 4️⃣ Reverse-engineering induction circuits


> ##### Learning objectives
> 
> - Understand the difference between investigating a circuit by looking at activtion patterns, and reverse-engineering a circuit by looking directly at the weights
> - Use the factored matrix class to inspect the QK and OV circuits within an induction circuit
> - Perform further exploration of induction circuits: composition scores, and targeted ablations


In previous exercises, we looked at the attention patterns and attributions of attention heads to try and identify which ones were important in the induction circuit. This might be a good way to get a feel for the circuit, but it's not a very rigorous way to understand it. It would be better described as **feature analysis**, where we observe *that* a particular head seems to be performing some task on a certain class of inputs, without identifying *why* it does so.

Now we're going to do some more rigorous mechanistic analysis - digging into the weights and using them to reverse engineer the induction head algorithm and verify that it is really doing what we think it is.


## Refresher - the induction circuit

Before we get into the meat of this section, let's refresh the results we've gotten so far from investigating induction heads. We've found:

* When fed repeated sequences of tokens, heads `1.4` and `1.10` have the characteristic induction head attention pattern of a diagonal stripe with offset `seq_len - 1`. 
    * We saw this both from the CircuitsVis results, and from the fact that these heads had high induction scores by our chosen metric (with all other heads having much lower scores).
* We also saw that head `0.7` strongly attends to the previous token in the sequence (even on non-repeated sequences).
* We performed **logit attribution** on the model, and found that the values written to the residual stream by heads `1.4` and `1.10` were both important for getting us correct predictions in the second half of the sequence.
* We performed **zero-ablation** on the model, and found that heads `0.7`, `1.4` and `1.10` all resulted in a large accuracy degradation on the repeated sequence task when they were ablated.

Based on all these observations, try and summarise the induction circuit and how it works, in your own words. You should try and link your explanation to the QK and OV circuits for particular heads, and describe what type (or types) of attention head composition are taking place.

You can use the dropdown below to check your understanding.

<details>
<summary>My summary of the algorithm</summary>

* Head `0.7` is a previous token head (the QK-circuit ensures it always attends to the previous token).
* The OV circuit of head `0.7` writes a copy of the previous token in a *different* subspace to the one used by the embedding.
* The output of head `0.7` is used by the *key* input of head `1.10` via K-Composition to attend to 'the source token whose previous token is the destination token'.
* The OV-circuit of head `1.10` copies the *value* of the source token to the same output logit.
    * Note that this is copying from the embedding subspace, *not* the `0.7` output subspace - it is not using V-Composition at all.
* `1.4` is also performing the same role as `1.10` (so together they can be more accurate - we'll see exactly how later).

To emphasise - the sophisticated hard part is computing the *attention* pattern of the induction head - this takes careful composition. The previous token and copying parts are fairly easy. This is a good illustrative example of how the QK circuits and OV circuits act semi-independently, and are often best thought of somewhat separately. And that computing the attention patterns can involve real and sophisticated computation!

Below is a diagram of the induction circuit, with the heads indicated in the weight matrices.

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/kcomp_diagram_described_3.png" width="900">
</details>


## Refresher - QK and OV circuits

Before we start, a brief terminology note. I'll refer to weight matrices for a particular layer and head using superscript notation, e.g. $W_Q^{1.4}$ is the query matrix for the 4th head in layer 1, and it has shape `[d_model, d_head]` (remember that we multiply with weight matrices on the right). Similarly, attention patterns will be denoted $A^{1.4}$ (remember that these are **activations**, not parameters, since they're given by the formula $A^h = x W_{QK}^h x^T$, where $x$ is the residual stream (with shape `[seq_len, d_model]`). 

As a shorthand, I'll often have $A$ denote the one-hot encoding of token `A` (i.e. the vector with zeros everywhere except a one at the index of `A`), so $A^T W_E$ is the embedding vector for `A`.

Lastly, I'll refer to special matrix products as follows:

* $W_{OV}^{h} := W_V^{h}W_O^{h}$ is the **OV circuit** for head $h$, and $W_E W_{OV}^h W_U$ is the **full OV circuit**. 
* $W_{QK}^h := W_Q^h (W_K^h)^T$ is the **QK circuit** for head $h$, and $W_E W_{QK}^h W_E^T$ is the **full QK circuit**. 

Note that the order of these matrices are slightly different from the **Mathematical Frameworks** paper - this is a consequence of the way TransformerLens stores its weight matrices.


#### Question - what is the interpretation of each of the following matrices?

*There are quite a lot of questions here, but they are conceptually important. If you're confused, you might want to read the answers to the first few questions and then try the later ones.*

In your answers, you should describe the type of input it takes, and what the outputs represent.

#### $W_{OV}^{h}$

<details>
<summary>Answer</summary>

$W_{OV}^{h}$ has size $(d_\text{model}, d_\text{model})$, it is a linear map describing **what information gets moved from source to destination, in the residual stream.**

In other words, if $x$ is a vector in the residual stream, then $x^T W_{OV}^{h}$ is the vector written to the residual stream at the destination position, if the destination token only pays attention to the source token at the position of the vector $x$.
</details>

#### $W_E W_{OV}^h W_U$

<details>
<summary>Hint</summary>

If $A$ is the one-hot encoding for token `A` (i.e. the vector with zeros everywhere except for a one in the position corresponding to token `A`), then think about what $A^T W_E W_{OV}^h W_U$ represents. You can evaluate this expression from left to right (e.g. start with thinking about what $A^T W_E$ represents, then multiply by the other two matrices).
</details>
<details>
<summary>Answer</summary>

$W_E W_{OV}^h W_U$ has size $(d_\text{vocab}, d_\text{vocab})$, it is a linear map describing **what information gets moved from source to destination, in a start-to-end sense.**

If $A$ is the one-hot encoding for token `A`, then:

* $A^T W_E$ is the embedding vector for `A`.
* $A^T W_E W_{OV}^h$ is the vector which would get written to the residual stream at the destination position, if the destination token only pays attention to `A`.
* $A^T W_E W_{OV}^h W_U$ is the unembedding of this vector, i.e. the thing which gets added to the final logits.

</details>

#### $W_{QK}^{h}$

<details>
<summary>Answer</summary>

$W_{QK}^{h}$ has size $(d_\text{model}, d_\text{model})$, it is a bilinear form describing **where information is moved to and from** in the residual stream (i.e. which residual stream vectors attend to which others).

$x_i^T W_{QK}^h x_j = (x_i^T W_Q^h) (x_j^T W_K^h)^T$ is the attention score paid by token $i$ to token $j$.
</details>

#### $W_E W_{QK}^h W_E^T$

<details>
<summary>Answer</summary>

$W_E W_{QK}^h W_E^T$ has size $(d_\text{vocab}, d_\text{vocab})$, it is a bilinear form describing **where information is moved to and from**, among words in our vocabulary (i.e. which tokens pay attention to which others).

If $A$ and $B$ are one-hot encodings for tokens `A` and `B`, then $A^T W_E W_{QK}^h W_E^T B$ is the attention score paid by token `A` to token `B`:

$$
A^T \, W_E\, W_{QK}^{h}\, W_E^T \, B = \underbrace{(A^T W_E W_Q^{h})}_{\text{query for token } A}  \underbrace{(B^T W_E W_K^{h})^T}_{\text{key for token }B}
$$
</details>

#### $W_{pos} W_{QK}^h W_{pos}^T$

<details>
<summary>Answer</summary>

$W_{pos} W_{QK}^h W_{pos}^T$ has size $(n_\text{ctx}, n_\text{ctx})$, it is a bilinear form describing **where information is moved to and from**, among words in our vocabulary (i.e. which tokens pay attention to which others).

If $i$ and $j$ are one-hot encodings for positions `i` and `j` (in other words they are just the ith and jth basis vectors), then $i^T W_{pos} W_{QK}^h W_{pos}^T j$ is the attention score paid by the token with position `i` to the token with position `j`:

$$
i^T \, W_{pos}\, W_{QK}^{h}\, W_{pos}^T \, j = \underbrace{(i^T W_{pos} W_Q^{h})}_{\text{query for i-th token}}  \underbrace{(j^T W_{pos} W_K^{h})^T}_{\text{key for j-th token}}
$$

</details>

#### $W_E W_{OV}^{h_1} W_{QK}^{h_2} W_E^T$ 

where $h_1$ is in an earlier layer than $h_2$.

<details>
<summary>Hint</summary>

This matrix is best seen as a bilinear form of size $(d_\text{vocab}, d_\text{vocab})$. The $(A, B)$-th element is:

$$
(A^T W_E W_{OV}^{h_1}) W_{QK}^{h_2} (B^T W_E)^T
$$
</details>

<details>
<summary>Answer</summary>

$W_E W_{OV}^{h_1} W_{QK}^{h_2} W_E^T$ has size $(n_\text{ctx}, n_\text{ctx})$, it is a bilinear form describing where information is moved to and from in head $h_2$, given that the **query-side vector** is formed from the output of head $h_1$. In other words, this is an instance of **Q-composition**.

If $A$ and $B$ are one-hot encodings for tokens `A` and `B`, then $A^T W_E W_{OV}^{h_1} W_{QK}^{h_2} W_E^T B$ is the attention score paid **to** token `B`, **by** any token which attended strongly to an `A`-token in head $h_1$.

---

To further break this down, if it still seems confusing:

$$
\begin{aligned}
A^T \, W_E\, W_{OV}^{h_1} W_{QK}^{h_2}\, W_E^T \, B &= \underbrace{(A^T W_E W_{OV}^{h_1}W_Q^{h_2})}_{\text{query of token which attended to A}}  \underbrace{(B^T W_E W_K^{h_2})^T}_\text{key of token B} \\
\end{aligned}
$$

---

Note that the actual attention score will be a sum of multiple terms, not just this one (in fact, we'd have a different term for every combination of query and key input). But this term describes the **particular contribution** to the attention score from this combination of query and key input, and it might be the case that this term is the only one that matters (i.e. all other terms don't much affect the final probabilities). We'll see something exactly like this later on.
</details>


Before we start, there's a problem that we might run into when calculating all these matrices. Some of them are massive, and might not fit on our GPU. For instance, both full circuit matrices have shape $(d_\text{vocab}, d_\text{vocab})$, which in our case means $50278\times 50278 \approx 2.5\times 10^{9}$ elements. Even if your GPU can handle this, it still seems inefficient. Is there any way we can meaningfully analyse these matrices, without actually having to calculate them?

## Factored Matrix class

In transformer interpretability, we often need to analyse low rank factorized matrices - a matrix $M = AB$, where M is `[large, large]`, but A is `[large, small]` and B is `[small, large]`. This is a common structure in transformers. 

For instance, we can factorise the OV circuit above as $W_{OV}^h = W_V^h W_O^h$, where $W_V^h$ has shape `[768, 64]` and $W_O^h$ has shape `[64, 768]`. For an even more extreme example, the full OV circuit can be written as $(W_E W_V^h) (W_O^h W_U)$, where these two matrices have shape `[50278, 64]` and `[64, 50278]` respectively. Similarly, we can write the full QK circuit as $(W_E W_Q^h) (W_E W_K^h)^T$.

The `FactoredMatrix` class is a convenient way to work with these. It implements efficient algorithms for various operations on these, such as computing the trace, eigenvalues, Frobenius norm, singular value decomposition, and products with other matrices. It can (approximately) act as a drop-in replacement for the original matrix.

This is all possible because knowing the factorisation of a matrix gives us a much easier way of computing its important properties. Intuitively, since $M=AB$ is a very large matrix that operates on very small subspaces, we shouldn't expect knowing the actual values $M_{ij}$ to be the most efficient way of storing it!


### Exercise - deriving properties of a factored matrix

```c
Difficulty: 🟠🟠🟠🟠⚪
Importance: 🟠🟠⚪⚪⚪

You shouldn't spend more than 10-25 minutes on this exercise.

If you're less interested in the maths, you can skip these exercises.
```

To give you an idea of what kinds of properties you can easily compute if you have a factored matrix, let's try and derive some ourselves.

Suppose we have $M=AB$, where $A$ has shape $(m, n)$, $B$ has shape $(n, m)$, and $m > n$. So $M$ is a size-$(m, m)$ matrix with rank at most $n$.

**Question - how can you easily compute the trace of $M$?**

<details>
<summary>Answer</summary>

The solution lies in the fact that trace is cyclic:

$$
\text{Tr}(M) = \text{Tr}(AB)
= \sum_{i,j=1}^n A_{ij} B_{ji}
= \sum_{i,j=1}^n B_{ji} A_{ij}
= \text{Tr}(BA)
$$

$AB$ is an $(m, m)$-matrix, but $BA$ is $(n, n)$ (much smaller). So we can just find the trace of $BA$ instead.
</details>

**Question - how can you easily compute the eigenvalues of $M$?**

(As you'll see in later exercises, eigenvalues are very important for evaluating matrices, for instance we can assess the [copying scores](https://transformer-circuits.pub/2021/framework/index.html#copying-matrix) of an OV circuit by looking at the eigenvalues of $W_{OV}$.)

<details>
<summary>Hint</summary>

It's computationally cheaper to find the eigenvalues of $BA$ rather than $AB$.

How are the eigenvalues of $AB$ and $BA$ related?
</details>
<details>
<summary>Answer</summary>

The eigenvalues of $AB$ and $BA$ are related as follows: if $\mathbf{v}$ is an eigenvector of $AB$ with $ABv = \lambda \mathbf{v}$, then $B\mathbf{v}$ is an eigenvector of $BA$ with the same eigenvalue:

$$
BA(B\mathbf{v}) = B (AB\mathbf{v}) = B (\lambda \mathbf{v}) = \lambda (B\mathbf{v})
$$

This only fails when $B\mathbf{v} = \mathbf{0}$, but in this case $AB\mathbf{v} = \mathbf{0}$ so $\lambda = 0$. Thus, we can conclude that any non-zero eigenvalues of $AB$ are also eigenvalues of $BA$.

It's much computationally cheaper to compute the eigenvalues of $BA$ (since it's a much smaller matrix), and this gives us all the non-zero eigenvalues of $AB$.
</details>

**Question (hard) - how can you easily compute the SVD of $M$?**

<details>
<summary>Hint</summary>

For a size-$(m, n)$ matrix with $m > n$, the [algorithmic complexity of finding SVD](https://en.wikipedia.org/wiki/Singular_value_decomposition#Numerical_approach) is $O(mn^2)$. So it's relatively cheap to find the SVD of $A$ and $B$ (complexity $mn^2$ vs $m^3$). Can you use that to find the SVD of $M$?
</details>


<details>
<summary>Answer</summary>

It's much cheaper to compute the SVD of the small matrices $A$ and $B$. Denote these SVDs by:

$$
\begin{aligned}
A &= U_A S_A V_A^T \\
B &= U_B S_B V_B^T
\end{aligned}
$$

where $U_A$ and $V_B$ are $(m, n)$, and the other matrices are $(n, n)$.

Then we have:

$$
\begin{aligned}
\quad\quad\quad\quad M &= AB \\
&= U_A (S_A V_A^T U_B S_B) V_B^T
\end{aligned}
$$

Note that the matrix in the middle has size $(n, n)$ (i.e. small), so we can compute its SVD cheaply:

$$
\begin{aligned}
\; S_A V_A^T U_B S_B &= U' S' {V'}^T \quad\quad\quad\quad\quad
\end{aligned}
$$

and finally, this gives us the SVD of $M$:

$$
\begin{aligned}
\quad\quad M &= U_A U' S' {V'}^T V_B^T \\
&= U S {V'}^T
\end{aligned}
$$

where $U = U_A U'$, $V = V_B V'$, and $S = S' S_B$.

All our SVD calculations and matrix multiplications had complexity at most $O(mn^2)$, which is much better than $O(m^3)$ (remember that we don't need to compute all the values of $U = U_A U'$, only the ones which correspond to non-zero singular values).
</details>

If you're curious, you can go to the `FactoredMatrix` documentation to see the implementation of the SVD calculation, as well as other properties and operations.


Now that we've discussed some of the motivations behind having a `FactoredMatrix` class, let's see it in action.

### Basic Examples

We can use the basic class directly - let's make a factored matrix directly and look at the basic operations:




```python

if MAIN:
    A = t.randn(5, 2)
    B = t.randn(2, 5)
    AB = A @ B
    AB_factor = FactoredMatrix(A, B)
    print("Norms:")
    print(AB.norm())
    print(AB_factor.norm())
    
    print(f"Right dimension: {AB_factor.rdim}, Left dimension: {AB_factor.ldim}, Hidden dimension: {AB_factor.mdim}")

```

We can also look at the eigenvalues and singular values of the matrix. Note that, because the matrix is rank 2 but 5 by 5, the final 3 eigenvalues and singular values are zero - the factored class omits the zeros.


```python

if MAIN:
    print("Eigenvalues:")
    print(t.linalg.eig(AB).eigenvalues)
    print(AB_factor.eigenvalues)
    print()
    print("Singular Values:")
    print(t.linalg.svd(AB).S)
    print(AB_factor.S)
    print("Full SVD:")
    print(AB_factor.svd())

```

<details>
<summary>Aside - the sizes of objects returned by the SVD method.</summary>

If $M = USV^T$, and `M.shape = (m, n)` and the rank is `r`, then the SVD method returns the matrices $U, S, V$. They have shape `(m, r)`, `(r,)`, and `(n, r)` respectively, because:

* We don't bother storing the off-diagonal entries of $S$, since they're all zero.
* We don't bother storing the columns of $U$ and $V$ which correspond to zero singular values, since these won't affect the value of $USV^T$.
</details>

We can multiply a factored matrix with an unfactored matrix to get another factored matrix (as in example below). We can also multiply two factored matrices together to get another factored matrix.


```python

if MAIN:
    C = t.randn(5, 300)
    ABC = AB @ C
    ABC_factor = AB_factor @ C
    print("Unfactored:", ABC.shape, ABC.norm())
    print("Factored:", ABC_factor.shape, ABC_factor.norm())
    print(f"Right dimension: {ABC_factor.rdim}, Left dimension: {ABC_factor.ldim}, Hidden dimension: {ABC_factor.mdim}")

```

If we want to collapse this back to an unfactored matrix, we can use the `AB` property to get the product:


```python

if MAIN:
    AB_unfactored = AB_factor.AB
    t.testing.assert_close(AB_unfactored, AB)

```

## Reverse-engineering circuits

Within our induction circuit, we have four individual circuits: the OV and QK circuits in our previous token head, and the OV and QK circuits in our attention head. In the following sections of the exercise, we'll reverse-engineer each of these circuits in turn.

* In the section **OV copying circuit**, we'll look at the layer-1 OV circuit.
* In the section **QK prev-token circuit**, we'll look at the layer-0 QK circuit.
* The third section (**K-composition**) is a bit trickier, because it involves looking at the composition of the layer-0 OV circuit **and** layer-1 QK circuit. We will have to do two things: 
    1. Show that these two circuits are composing (i.e. that the output of the layer-0 OV circuit is the main determinant of the key vectors in the layer-1 QK circuit).
    2. Show that the joint operation of these two circuits is "make the second instance of a token attend to the token *following* an earlier instance.

The dropdown below contains a diagram explaining how the three sections relate to the different components of the induction circuit. You might have to open it in a new tab to see it clearly.

<details>
<summary>Diagram</summary>

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/kcomp_diagram_described_2_new.png" width="1400">
</details>

After this, we'll have a look at composition scores, which are a more mathematically justified way of showing that two attention heads are composing (without having to look at their behaviour on any particular class of inputs, since it is a property of the actual model weights).


## [1] OV copying circuit

Let's start with an easy parts of the circuit - the copying OV circuit of `1.4` and `1.10`. Let's start with head 4. The only interpretable (read: **privileged basis**) things here are the input tokens and output logits, so we want to study the matrix:

$$
W_E W_{OV}^{1.4} W_U
$$ 

(and same for `1.10`). This is the $(d_\text{vocab}, d_\text{vocab})$-shape matrix that combines with the attention pattern to get us from input to output.

We want to calculate this matrix, and inspect it. We should find that its diagonal values are very high, and its non-diagonal values are much lower.

**Question - why should we expect this observation?** (you may find it helpful to refer back to the previous section, where you described what the interpretation of different matrices was.)

<details>
<summary>Hint</summary>

Suppose our repeating sequence is `A B ... A B`. Let $A$, $B$ be the corresponding one-hot encoded tokens. The `B`-th row of this matrix is:

$$
B^T W_E W_{OV}^{1.4} W_U
$$

What is the interpretation of this expression, in the context of our attention head?
</details>

<details>
<summary>Answer</summary>

If our repeating sequence is `A B ... A B`, then:

$$
B^T W_E W_{OV}^{1.4} W_U
$$

is the **vector of logits which gets moved from the first `B` token to the second `A` token, to be used as the prediction for the token following the second `A` token**. It should result in a high prediction for `B`, and a low prediction for everything else. In other words, the `(B, X)`-th element of this matrix should be highest for `X=B`, which is exactly what we claimed.

---

If this still seems confusing, let's break it down bit by bit. We have:

* $B^T W_E$ is the token-embedding of `B`.
* $B^T W_E W_{OV}^{1.4}$ is the vector which gets moved from the first `B` token to the second `A` token, by our attention head (because the second `A` token attends strongly to the first `B`).
* $B^T W_E W_{OV}^{1.4} W_U$ is the vector of logits representing how this attention head affects the prediction of the token following the second `A`. There should be a higher logit for `B` than for any other token, because the attention head is trying to copy `B` to the second `A`.

---

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/kcomp_diagram_described-OV-last.png" width="400">

</details>


### Exercise - compute OV circuit for `1.4`

*This is the first of several similar exercises where you calculate a circuit by multiplying matrices. This exercise is pretty important (in particular, you should make sure you understand what this matrix represents and why we're interested in it), but the actual calculation shouldn't take very long.*


You should compute it as a `FactoredMatrix` object.

Remember, you can access the model's weights directly e.g. using `model.W_E` or `model.W_Q` (the latter gives you all the `W_Q` matrices, indexed by layer and head).

```python
if MAIN:
    # YOUR CODE HERE - compute OV circuit
   
    tests.test_full_OV_circuit(full_OV_circuit, model, layer, head_index)
```

<details>
<summary>Help - I'm not sure how to use this class to compute a product of more than 2 matrices.</summary>

You can compute it directly, as:

```python
full_OV_circuit = FactoredMatrix(W_E @ W_V, W_O @ W_U)
```

Alternatively, another nice feature about the `FactoredMatrix` class is that you can chain together matrix multiplications. The following code defines exactly the same `FactoredMatrix` object:

```python
OV_circuit = FactoredMatrix(W_V, W_O)
full_OV_circuit = W_E @ OV_circuit @ W_U
```
</details>

<details>
<summary>Solution</summary>

```python
head_index = 4
layer = 1

W_O = model.W_O[layer, head_index]
W_V = model.W_V[layer, head_index]
W_E = model.W_E
W_U = model.W_U

OV_circuit = FactoredMatrix(W_V, W_O)
full_OV_circuit = W_E @ OV_circuit @ W_U
```
</details>


### Exercise - verify this is the identity

```c
Difficulty: 🟠🟠⚪⚪⚪
Importance: 🟠🟠🟠⚪⚪

You shouldn't spend more than 5-10 minutes on this exercise.

This exercise should be very short; it only requires 2 lines of code. Understanding it conceptually is more important than the actual coding.
```


Now we want to check that this matrix is the identity. Since it's in factored matrix form, this is a bit tricky, but there are still things we can do.

First, to validate that it looks diagonal-ish, let's pick 200 random rows and columns and visualise that - it should at least look identity-ish here!


```python

if MAIN:
    # YOUR CODE HERE - get a random sample from the full OV circuit, so it can be plotted with `imshow`
    imshow(
        full_OV_circuit_sample,
        labels={"x": "Input token", "y": "Logits on output token"},
        title="Full OV circuit for copying head",
        width=700,
    )

```

<details>
<summary>Aside - indexing factored matrices</summary>

Yet another nice thing about factored matrices is that you can evaluate small submatrices without having to compute the entire matrix. This is based on the fact that the `[i, j]`-th element of matrix `AB` is `A[i, :] @ B[:, j]`.

When you index a factored matrix, you get back another factored matrix. So rather than explicitly calculating `A[left_indices, :] @ B[:, left_indices]`, we can just write `AB[left_indices, left_indices]`.
</details>

<details>
<summary>Solution</summary>


```python
indices = t.randint(0, model.cfg.d_vocab, (200,))
full_OV_circuit_sample = full_OV_circuit[indices, indices].AB

```
</details>

You should observe a pretty distinct diagonal pattern here, which is a good sign. However, the matrix is pretty noisy so it probably won't be exactly the identity. Instead, we should come up with a summary statistic to capture a rough sense of "closeness to the identity".

**Accuracy** is a good summary statistic - what fraction of the time is the largest logit in a row on the diagonal? Even if there's lots of noise, you'd probably still expect the largest logit to be on the diagonal a good deal of the time.

If you're on a Colab or have a powerful GPU, you should be able to compute the full matrix and perform this test. If not, the most efficient method is to iterate through the rows (or batches of rows). Remember - if `M = AB` is a factored matrix, then the $i$th row of `M` is `A[i, :] @ B`.

Bonus exercise: Top-5 accuracy is also a good metric (use `t.topk`, take the indices output).


```python
def top_1_acc(full_OV_circuit: FactoredMatrix) -> float:
    '''
    This should take the argmax of each column (ie over dim=0) and return the fraction of the time that's equal to the correct logit
    '''
    pass


if MAIN:
    print(f"Fraction of the time that the best logit is on the diagonal: {top_1_acc(full_OV_circuit):.4f}")

```

<details>
<summary>Solution </summary>

```python
def top_1_acc(full_OV_circuit: FactoredMatrix) -> float:
    '''
    This should take the argmax of each column (ie over dim=0) and return the fraction of the time that's equal to the correct logit
    '''
    # SOLUTION
    AB = full_OV_circuit.AB

    return (t.argmax(AB, dim=1) == t.arange(AB.shape[0]).to(device)).float().mean().item()
```

or a solution using iteration (not that this should be necessary for the GPUs we're working on, but still it's useful to understand):

```python
def top_1_acc_iteration(full_OV_circuit: FactoredMatrix, batch_size: int = 100) -> float: 
    '''
    This should take the argmax of each column (ie over dim=0) and return the fraction of the time that's equal to the correct logit
    '''
    # SOLUTION
    A, B = full_OV_circuit.A, full_OV_circuit.B
    nrows = full_OV_circuit.shape[0]
    nrows_max_on_diagonal = 0

    for i in tqdm(range(0, nrows + batch_size, batch_size)):
        rng = range(i, min(i + batch_size, nrows))
        if rng:
            submatrix = A[rng, :] @ B
            diag_indices = t.tensor(rng, device=submatrix.device)
            nrows_max_on_diagonal += (submatrix.argmax(-1) == diag_indices).float().sum().item()
    
    return nrows_max_on_diagonal / nrows
```

And for top-5:

```python
def top_5_acc_iteration(full_OV_circuit: FactoredMatrix, batch_size: int = 100) -> float:
    '''
    This should take the argmax of each column (ie over dim=0) and return the fraction of the time that's equal to the correct logit
    '''
    A, B = full_OV_circuit.A, full_OV_circuit.B
    nrows = full_OV_circuit.shape[0]
    nrows_top5_on_diagonal = 0

    for i in tqdm(range(0, nrows + batch_size, batch_size)):
        rng = range(i, min(i + batch_size, nrows))
        if rng:
            submatrix = A[rng, :] @ B
            diag_indices = t.tensor(rng, device=submatrix.device).unsqueeze(-1)
            top5 = t.topk(submatrix, k=5).indices
            nrows_top5_on_diagonal += (diag_indices == top5).sum().item()

    return nrows_top5_on_diagonal / nrows

if MAIN:
    print(f"Fraction of the time that one of the top 5 best logits is on the diagonal: {top_5_acc_iteration(full_OV_circuit):.4f}")
```
</details>

This should return about 30.79% - pretty underwhelming. It goes up to 47.73% for top-5. What's up with that?


### Exercise - compute effective circuit

```c
Difficulty: 🟠🟠⚪⚪⚪
Importance: 🟠🟠🟠⚪⚪

You shouldn't spend more than 5-10 minutes on this exercise.

This exercise should be very short; it only requires 2 lines of code. Understanding it conceptually is more important than the actual coding.
```


Now we return to why we have *two* induction heads. If both have the same attention pattern, the effective OV circuit is actually $W_U(W_O^{1.4}W_V^{1.4}+W_O^{1.10}W_V^{1.10})W_E$, and this is what matters. So let's re-run our analysis on this!

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/effective_ov_circuit.png" width="650">


<details>
<summary>Question - why might the model want to split the circuit across two heads?</summary>

Because $W_V W_O$ is a rank 64 matrix. The sum of two is a rank 128 matrix. This can be a significantly better approximation to the desired 50K x 50K matrix!
</details>


```python
# YOUR CODE HERE - compute the effective OV circuit, and run `top_1_acc` on it

```

<details>
<summary>Solution (and expected output)</summary>

```python
W_O_both = einops.rearrange(model.W_O[1, [4, 10]], "head d_head d_model -> (head d_head) d_model")
W_V_both = einops.rearrange(model.W_V[1, [4, 10]], "head d_model d_head -> d_model (head d_head)")

W_OV_eff = W_E @ FactoredMatrix(W_V_both, W_O_both) @ W_U

print(f"Fraction of the time that the best logit is on the diagonal: {top_1_acc(W_OV_eff):.4f}")
```

You should get an accuracy of 95.6% for top-1, and 98% for top-5 - much better!
</details>


## [2] QK prev-token circuit

The other easy circuit is the QK-circuit of L0H7 - how does it know to be a previous token circuit?

We can multiply out the full QK circuit via the positional embeddings: 

$$
W_\text{pos} W_Q^{0.7} (W_K^{0.7})^T W_\text{pos}^T
$$

to get a matrix `pos_by_pos` of shape `[max_ctx, max_ctx]` (max ctx = max context length, i.e. maximum length of a sequence we're allowing, which is set by our choice of dimensions in $W_\text{pos}$).

Note that in this case, our max context window is 2048 (we can check this via `model.cfg.n_ctx`). This is much smaller than the 50k-size matrices we were working with in the previous section, so we shouldn't need to use the factored matrix class here.

Once we calculate it, we can then mask it and apply a softmax, and should get a clear stripe on the lower diagonal (Tip: Click and drag to zoom in, hover over cells to see their values and indices!)


<details>
<summary>Question - why should we expect this matrix to have a lower-diagonal stripe?</summary>

The full QK circuit $W_\text{pos} W_{QK}^{0.7} W_\text{pos}^T$ has shape `[n_ctx, n_ctx]`. It is a bilinear form, with the $(i, j)$-th element representing the attention score paid by the $i$-th token to the $j$-th token. This should be very large when $j = i - 1$ (and smaller for all other values of $j$), because this is a **previous head token**. So if we softmax over $j$, we should get a lower-diagonal stripe of 1.

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/kcomp_diagram_described-QK-last.png" width="600">

</details>

Why is it justified to ignore token encodings? In this case, it turns out that the positional encodings have a much larger effect on the attention scores than the token encodings. If you want, you can verify this for yourself - after going through the next section (reverse-engineering K-composition), you'll have a better sense of how to perform attribution on the inputs to attention heads, and assess their importance).




### Exercise - compute full QK-circuit for `0.7`

```c
Difficulty: 🟠🟠🟠⚪⚪
Importance: 🟠🟠🟠⚪⚪

You shouldn't spend more than 10-15 minutes on this exercise.

The fiddly masking and scaling steps make this exercise a bit harder than the last one. Look at the solution if you don't see where you're going wrong.
```

*This is another relatively simple matrix multiplication, although it's a bit fiddly on account of the  masking and scaling steps. If you understand what you're being asked to do but still not passing the tests, you should probably look at the solution.*


Now, you should compute and plot the matrix.

Remember, you're calculating the attention pattern (i.e. probabilites) not the scores. You'll need to mask the scores (you can use the `mask_scores` function we've provided you with), and scale them.




```python
def mask_scores(attn_scores: Float[Tensor, "query_nctx key_nctx"]):
    '''Mask the attention scores so that tokens don't attend to previous tokens.'''
    assert attn_scores.shape == (model.cfg.n_ctx, model.cfg.n_ctx)
    mask = t.tril(t.ones_like(attn_scores)).bool()
    neg_inf = t.tensor(-1.0e6).to(attn_scores.device)
    masked_attn_scores = t.where(mask, attn_scores, neg_inf)
    return masked_attn_scores



if MAIN:
    # YOUR CODE HERE - calculate the matrix `pos_by_pos_pattern` as described above
    tests.test_pos_by_pos_pattern(pos_by_pos_pattern, model, layer, head_index)

```

<details>
<summary>Solution</summary>


```python
layer = 0
head_index = 7
W_pos = model.W_pos
W_QK = model.W_Q[layer, head_index] @ model.W_K[layer, head_index].T
pos_by_pos_scores = W_pos @ W_QK @ W_pos.T
masked_scaled = mask_scores(pos_by_pos_scores / model.cfg.d_head ** 0.5)
pos_by_pos_pattern = t.softmax(masked_scaled, dim=-1)

```
</details>


Once the tests pass, you can plot a corner of your matrix:


```python

if MAIN:
    print(f"Avg lower-diagonal value: {pos_by_pos_pattern.diag(-1).mean():.4f}")
    
    imshow(
        utils.to_numpy(pos_by_pos_pattern[:100, :100]), 
        labels={"x": "Key", "y": "Query"}, 
        title="Attention patterns for prev-token QK circuit, first 100 indices",
        width=700
    )

```

## [3] K-composition circuit

We now dig into the hard part of the circuit - demonstrating the K-Composition between the previous token head and the induction head.

#### Splitting activations

We can repeat the trick from the logit attribution scores. The QK-input for layer 1 is the sum of 14 terms (2+n_heads) - the token embedding, the positional embedding, and the results of each layer 0 head. So for each head $\text{H}$ in layer 1, the query tensor (ditto key) corresponding to sequence position $i$ is:

$$
\begin{align*}
x W^\text{1.H}_Q &= (e + pe + \sum_{h=0}^{11} x^\text{0.h}) W^\text{1.H}_Q \\
&= e W^\text{1.H}_Q + pe W^\text{1.H}_Q + \sum_{h=0}^{11} x^\text{0.h} W^\text{1.H}_Q
\end{align*}
$$

where $e$ stands for the token embedding, $pe$ for the positional embedding, and $x^\text{0.h}$ for the output of head $h$ in layer 0 (and the sum of these tensors equals the residual stream $x$). All these tensors have shape `[seq, d_model]`. So we can treat the expression above as a sum of matrix multiplications `[seq, d_model] @ [d_model, d_head] -> [seq, d_head]`. 

For ease of notation, I'll refer to the 14 inputs as $(y_0, y_1, ..., y_{13})$ rather than $(e, pe, x^\text{0.h}, ..., x^{11.h})$. So we have:

$$
x W^h_Q = \sum_{i=0}^{13} y_i W^h_Q
$$

with each $y_i$ having shape `[seq, d_model]`, and the sum of $y_i$s being the full residual stream $x$. Here is a diagram to illustrate:

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/components.png" width="550">


### Exercise - analyse the relative importance

```c
Difficulty: 🟠🟠🟠🟠⚪
Importance: 🟠🟠🟠🟠⚪

You shouldn't spend more than 15-25 minutes on these exercises.

Most of these functions just involve indexing and einsums, but conceptual understanding / figuring out exactly what the question is asking for is the hard part!
```


We can now analyse the relative importance of these 14 terms! A very crude measure is to take the norm of each term (by component and position).

Note that this is a pretty dodgy metric - q and k are not inherently interpretable! But it can be a good and easy-to-compute proxy.

<details>
<summary>Question - why are Q and K not inherently interpretable? Why might the norm be a good metric in spite of this?</summary>

They are not inherently interpretable because they operate on the residual stream, which doesn't have a **privileged basis**. You could stick a rotation matrix $R$ after all of the $Q$, $K$ and $V$ weights (and stick a rotation matrix before everything that writes to the residual stream), and the model would still behave exactly the same.

The reason taking the norm is still a reasonable thing to do is that, despite the individual elements of these vectors not being inherently interpretable, it's still a safe bet that if they are larger than they will have a greater overall effect on the residual stream. So looking at the norm doesn't tell us how they work, but it does indicate which ones are more important.
</details>

Fill in the functions below:


```python
def decompose_qk_input(cache: ActivationCache) -> t.Tensor:
    '''
    Output is decomposed_qk_input, with shape [2+num_heads, seq, d_model]

    The [i, :, :]th element is y_i (from notation above)
    '''
    pass

def decompose_q(decomposed_qk_input: t.Tensor, ind_head_index: int) -> t.Tensor:
    '''
    Output is decomposed_q with shape [2+num_heads, position, d_head]

    The [i, :, :]th element is y_i @ W_Q (so the sum along axis 0 is just the q-values)
    '''
    pass

def decompose_k(decomposed_qk_input: t.Tensor, ind_head_index: int) -> t.Tensor:
    '''
    Output is decomposed_k with shape [2+num_heads, position, d_head]

    The [i, :, :]th element is y_i @ W_K (so the sum along axis 0 is just the k-values)
    '''
    pass


if MAIN:
    ind_head_index = 4
    # First we get decomposed q and k input, and check they're what we expect
    decomposed_qk_input = decompose_qk_input(rep_cache)
    decomposed_q = decompose_q(decomposed_qk_input, ind_head_index)
    decomposed_k = decompose_k(decomposed_qk_input, ind_head_index)
    t.testing.assert_close(decomposed_qk_input.sum(0), rep_cache["resid_pre", 1] + rep_cache["pos_embed"], rtol=0.01, atol=1e-05)
    t.testing.assert_close(decomposed_q.sum(0), rep_cache["q", 1][:, ind_head_index], rtol=0.01, atol=0.001)
    t.testing.assert_close(decomposed_k.sum(0), rep_cache["k", 1][:, ind_head_index], rtol=0.01, atol=0.01)
    # Second, we plot our results
    component_labels = ["Embed", "PosEmbed"] + [f"0.{h}" for h in range(model.cfg.n_heads)]
    for decomposed_input, name in [(decomposed_q, "query"), (decomposed_k, "key")]:
        imshow(
            utils.to_numpy(decomposed_input.pow(2).sum([-1])), 
            labels={"x": "Position", "y": "Component"},
            title=f"Norms of components of {name}", 
            y=component_labels,
            width=1000, height=400
        )

```

<details>
<summary>Solution</summary>


You should see that the most important query components are the token and positional embeddings. The most important key components are those from $y_9$, which is $x_7$, i.e. from head `0.7`.
```python
def decompose_qk_input(cache: ActivationCache) -> t.Tensor:
    '''
    Output is decomposed_qk_input, with shape [2+num_heads, seq, d_model]

    The [i, :, :]th element is y_i (from notation above)
    '''
    # SOLUTION
    y0 = cache["embed"].unsqueeze(0) # shape (1, seq, d_model)
    y1 = cache["pos_embed"].unsqueeze(0) # shape (1, seq, d_model)
    y_rest = cache["result", 0].transpose(0, 1) # shape (12, seq, d_model)

    return t.concat([y0, y1, y_rest], dim=0)

def decompose_q(decomposed_qk_input: t.Tensor, ind_head_index: int) -> t.Tensor:
    '''
    Output is decomposed_q with shape [2+num_heads, position, d_head]

    The [i, :, :]th element is y_i @ W_Q (so the sum along axis 0 is just the q-values)
    '''
    # SOLUTION
    W_Q = model.W_Q[1, ind_head_index]

    return einops.einsum(
        decomposed_qk_input, W_Q,
        "n seq d_head, d_head d_model -> n seq d_model"
    )

def decompose_k(decomposed_qk_input: t.Tensor, ind_head_index: int) -> t.Tensor:
    '''
    Output is decomposed_k with shape [2+num_heads, position, d_head]

    The [i, :, :]th element is y_i @ W_K(so the sum along axis 0 is just the k-values)
    '''
    # SOLUTION
    W_K = model.W_K[1, ind_head_index]

    return einops.einsum(
        decomposed_qk_input, W_K,
        "n seq d_head, d_head d_model -> n seq d_model"
    )
```
</details>

<details>
<summary>A technical note on the positional embeddings - optional, feel free to skip this.</summary>

You might be wondering why the tests compare the decomposed qk sum with the sum of the `resid_pre + pos_embed`, rather than just `resid_pre`. The answer lies in how we defined the transformer, specifically in this line from the config:

```python
positional_embedding_type="shortformer"
```

The result of this is that the positional embedding isn't added to the residual stream. Instead, it's added as inputs to the Q and K calculation (i.e. we calculate `(resid_pre + pos_embed) @ W_Q` and same for `W_K`), but **not** as inputs to the V calculation (i.e. we just calculate `resid_pre @ W_V`). This isn't actually how attention works in general, but for our purposes it makes the analysis of induction heads cleaner because we don't have positional embeddings interfering with the OV circuit.

**Question - this type of embedding actually makes it impossible for attention heads to form via Q-composition. Can you see why?**
</details>

This tells us which heads are probably important, but we can do better than that. Rather than looking at the query and key components separately, we can see how they combine together - i.e. take the decomposed attention scores.

This is a bilinear function of q and k, and so we will end up with a `decomposed_scores` tensor with shape `[query_component, key_component, query_pos, key_pos]`, where summing along BOTH of the first axes will give us the original attention scores (pre-mask).


### Exercise - decompose attention scores

```c
Difficulty: 🟠🟠⚪⚪⚪
Importance: 🟠🟠🟠🟠⚪

You shouldn't spend more than 5-10 minutes on this exercise.

Having already done the previous exercises, this one should be easier.
```

Implement the function giving the decomposed scores (remember to scale by `sqrt(d_head)`!) For now, don't mask it.

<details>
<summary>Question - why do I focus on the attention scores, not the attention pattern? (i.e. pre softmax not post softmax)</summary>

Because the decomposition trick *only* works for things that are linear - softmax isn't linear and so we can no longer consider each component independently.
</details>

<details>
<summary>Help - I'm confused about what we're doing / why we're doing it.</summary>

Remember that each of our components writes to the residual stream separately. So after layer 1, we have:

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/components.png" width="650">

We're particularly interested in the attention scores computed in head `1.4`, and how they depend on the inputs into that head. We've already decomposed the residual stream value $x$ into its terms $e$, $pe$, and $x^ 0$ through $x^{11}$ (which we've labelled $y_0, ..., y_{13}$ for simplicity), and we've done the same for key and query terms. We can picture these terms being passed into head `1.4` as:

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/components-2.png" width="650">

So when we expand `attn_scores` out in full, they are a sum of $14^2 = 196$ terms - one for each combination of `(query_component, key_component)`.

---

#### Why is this decomposition useful?

We have a theory about a particular circuit in our model. We think that head `1.4` is an attention head, and the most important components that feed into this head are the prev token head `0.7` (as key) and the token embedding (as query). This is already supported by the evidence of our magnitude plots above (because we saw that `0.7` as key and token embeddings as query were large), but we still don't know how this particular key and query work **together**; we've only looked at them separately.

By decomposing `attn_scores` like this, we can check whether the contribution from combination `(query=tok_emb, key=0.7)` is indeed producing the characteristic induction head pattern which we've observed (and the other 195 terms don't really matter).
</details>


```python
def decompose_attn_scores(decomposed_q: t.Tensor, decomposed_k: t.Tensor) -> t.Tensor:
    '''
    Output is decomposed_scores with shape [query_component, key_component, query_pos, key_pos]
    
    The [i, j, :, :]th element is y_i @ W_QK @ y_j^T (so the sum along both first axes are the attention scores)
    '''
    pass


if MAIN:
    tests.test_decompose_attn_scores(decompose_attn_scores, decomposed_q, decomposed_k)

```

<details>
<summary>Solution</summary>


```python
def decompose_attn_scores(decomposed_q: t.Tensor, decomposed_k: t.Tensor) -> t.Tensor:
    '''
    Output is decomposed_scores with shape [query_component, key_component, query_pos, key_pos]
    
    The [i, j, :, :]th element is y_i @ W_QK @ y_j^T (so the sum along both first axes are the attention scores)
    '''
    # SOLUTION
    return einops.einsum(
        decomposed_q, decomposed_k,
        "q_comp q_pos d_model, k_comp k_pos d_model -> q_comp k_comp q_pos k_pos",
    )
```
</details>


Once these tests have passed, you can plot the results:


```python

if MAIN:
    decomposed_scores = decompose_attn_scores(decomposed_q, decomposed_k)
    decomposed_stds = einops.reduce(
        decomposed_scores, 
        "query_decomp key_decomp query_pos key_pos -> query_decomp key_decomp", 
        t.std
    )
    
    # First plot: attention score contribution from (query_component, key_component) = (Embed, L0H7)
    imshow(
        utils.to_numpy(t.tril(decomposed_scores[0, 9])), 
        title="Attention score contributions from (query, key) = (embed, output of L0H7)",
        width=800
    )
    
    # Second plot: std dev over query and key positions, shown by component
    imshow(
        utils.to_numpy(decomposed_stds), 
        labels={"x": "Key Component", "y": "Query Component"},
        title="Standard deviations of attention score contributions (by key and query component)", 
        x=component_labels, 
        y=component_labels,
        width=800
    )

```

<details>
<summary>Question - what is the interpretation of these plots?</summary>

The first plot tells you that the term $e W_{QK}^{1.4} (x^{0.7})^T$ (i.e. the component of the attention scores for head `1.4` where the query is supplied by the token embeddings and the key is supplied by the output of head `0.7`) produces the distinctive attention pattern we see in the induction head: a strong diagonal stripe.

Although this tells us that this this component would probably be sufficient to implement the induction mechanism, it doesn't tell us the whole story. Ideally, we'd like to show that the other 195 terms are unimportant. Taking the standard deviation across the attention scores for a particular pair of components is a decent proxy for how important this term is in the overall attention pattern. The second plot shows us that the standard deviation is very small for all the other components, so we can be confident that the other components are unimportant.

To summarise:

* The first plot tells us that the pair `(q_component=tok_emb, k_component=0.7)` produces the characteristic induction-head pattern we see in attention head `1.4`.
* The second plot confirms that this pair is the only important one for influencing the attention pattern in `1.4`; all other pairs have very small contributions.
</details>

### Interpreting the full circuit

Now we know that head `1.4` is composing with head `0.7` via K composition, we can multiply through to create a full circuit:

$$
W_E\, W_{QK}^{1.4}\, (W_{OV}^{0.7})^T\, W_E^T
$$

and verify that it's the identity. (Note, when we say identity here, we're again thinking about it as a distribution over logits, so this should be taken to mean "high diagonal values", and we'll be using our previous metric of `top_1_acc`.)

#### Question - why should this be the identity?

<details>
<summary>Answer</summary>

This matrix is a bilinear form. Its diagonal elements $(A, A)$ are:

$$
A^T \, W_E\, W_{QK}^{1.4}\, W_{OV}^{0.7}\, W_E^T \, A = \underbrace{(A^T W_E W_Q^{1.4})}_{\text{query}} \underbrace{(A^T W_E W_{OV}^{0.7} W_K^{1.4})^T}_{\text{key}}
$$

Intuitively, the query is saying **"I'm looking for a token which followed $A$"**, and the key is saying **"I *am* a token which folllowed $A$"** (recall that $A^T W_E W_{OV}^{0.7}$ is the vector which gets moved one position forward by our prev token head `0.7`).

Now, consider the off-diagonal elements $(A, X)$ (for $X \neq A$). We expect these to be small, because the key doesn't match the query:

$$
A^T \, W_E\, W_{QK}^{1.4}\, W_{OV}^{0.7}\, W_E^T \, X = \underbrace{(\text{I'm looking for a token which followed A})}_\text{query} \boldsymbol{\cdot} \underbrace{(\text{I am a token which followed X})}_{\text{key}}
$$


Hence, we expect this to be the identity.

An illustration:

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/kcomp_diagram_described-K-last.png" width="700">

</details>


### Exercise - compute the K-comp circuit

```c
Difficulty: 🟠🟠🟠⚪⚪
Importance: 🟠🟠🟠🟠⚪

You shouldn't spend more than 10-20 minutes on this exercise.
```

Calculate the matrix above, as a `FactoredMatrix` object.

<details>
<summary>Aside about multiplying FactoredMatrix objects together.</summary>

If  `M1 = A1 @ B1` and `M2 = A2 @ B2` are factored matrices, then `M = M1 @ M2` returns a new factored matrix. This might be:

```python
FactoredMatrix(M1.AB @ M2.A, M2.B)
```

or it might be:

```python
FactoredMatrix(M1.A, M1.B @ M2.AB)
```

with these two objects corresponding to the factorisations $M = (A_1 B_1 A_2) (B_2)$ and $M = (A_1) (B_1 A_2 B_2)$ respectively.

Which one gets returned depends on the size of the hidden dimension, e.g. `M1.mdim < M2.mdim` then the factorisation used will be $M = A_1 B_1 (A_2 B_2)$.

Remember that both these factorisations are valid, and will give you the exact same SVD. The only reason to prefer one over the other is for computational efficiency (we prefer a smaller bottleneck dimension, because this determines the computational complexity of operations like finding SVD).
</details>


```python
def find_K_comp_full_circuit(
    model: HookedTransformer,
    prev_token_head_index: int,
    ind_head_index: int
) -> FactoredMatrix:
    '''
    Returns a (vocab, vocab)-size FactoredMatrix, with the first dimension being the query side and the second dimension being the key side (going via the previous token head)
    '''
    pass


if MAIN:
    prev_token_head_index = 7
    ind_head_index = 4
    K_comp_circuit = find_K_comp_full_circuit(model, prev_token_head_index, ind_head_index)
    
    tests.test_find_K_comp_full_circuit(find_K_comp_full_circuit, model)
    
    print(f"Fraction of tokens where the highest activating key is the same token: {top_1_acc(K_comp_circuit.T):.4f}")

```

<details>
<summary>Solution</summary>


```python
def find_K_comp_full_circuit(
    model: HookedTransformer,
    prev_token_head_index: int,
    ind_head_index: int
) -> FactoredMatrix:
    '''
    Returns a (vocab, vocab)-size FactoredMatrix, with the first dimension being the query side and the second dimension being the key side (going via the previous token head)
    '''
    # SOLUTION
    W_E = model.W_E
    W_Q = model.W_Q[1, ind_head_index]
    W_K = model.W_K[1, ind_head_index]
    W_O = model.W_O[0, prev_token_head_index]
    W_V = model.W_V[0, prev_token_head_index]

    Q = W_E @ W_Q
    K = W_E @ W_V @ W_O @ W_K
    return FactoredMatrix(Q, K.T)
```
</details>

You can also try this out for `ind_head_index = 10`. Do you get a better result?

Note - unlike last time, it doesn't make sense to consider the "effective circuit" formed by adding together the weight matrices for heads `1.4` and `1.10`. Why not?

<details>
<summary>Answer</summary>

Because the weight matrices we're dealing with here are from the QK circuit, not the OV circuit. These don't get combined in a linear way; instead we take softmax over each head's QK-circuit output individually.
</details>

## Further Exploration of Induction Circuits

I now consider us to have fully reverse engineered an induction circuit - by both interpreting the features and by reverse engineering the circuit from the weights. But there's a bunch more ideas that we can apply for finding circuits in networks that are fun to practice on induction heads, so here's some bonus content - feel free to skip to the later bonus ideas though.

### Composition scores

A particularly cool idea in the paper is the idea of [virtual weights](https://transformer-circuits.pub/2021/framework/index.html#residual-comms), or compositional scores. (Though I came up with it, so I'm deeply biased!). This is used [to identify induction heads](https://transformer-circuits.pub/2021/framework/index.html#analyzing-a-two-layer-model).

The key idea of compositional scores is that the residual stream is a large space, and each head is reading and writing from small subspaces. By default, any two heads will have little overlap between their subspaces (in the same way that any two random vectors have almost zero dot product in a large vector space). But if two heads are deliberately composing, then they will likely want to ensure they write and read from similar subspaces, so that minimal information is lost. As a result, we can just directly look at "how much overlap there is" between the output space of the earlier head and the K, Q, or V input space of the later head. 

We represent the **output space** with $W_{OV}=W_V W_O$. Call matrices like this $W_A$.

We represent the **input space** with $W_{QK}=W_Q W_K^T$ (for Q-composition), $W_{QK}^T=W_K  W_Q^T$ (for K-Composition) or $W_{OV}=W_V W_O$ (for V-Composition, of the later head). Call matrices like these $W_B$ (we've used this notation so that $W_B$ refers to a later head, and $W_A$ to an earlier head).

<details>
<summary>Help - I don't understand what motivates these definitions.</summary>

Recall that we can view each head as having three input wires (keys, queries and values), and one output wire (the outputs). The different forms of composition come from the fact that keys, queries and values can all be supplied from the output of a different head.

Here is an illustration which shows the three different cases, and should also explain why we use this terminology. You might have to open it in a new tab to see it clearly.

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/composition_new.png" width="1400">

</details>

How do we formalise overlap? This is basically an open question, but a surprisingly good metric is $\frac{\|W_AW_B\|_F}{\|W_B\|_F\|W_A\|_F}$ where $\|W\|_F=\sqrt{\sum_{i,j}W_{i,j}^2}$ is the Frobenius norm, the sum of squared elements. (If you're dying of curiosity as to what makes this a good metric, you can jump to the section immediately after the exercises below.)


### Exercise - calculate composition scores

```c
Difficulty: 🟠🟠🟠⚪⚪
Importance: 🟠🟠🟠⚪⚪

You shouldn't spend more than 15-25 minutes on these exercises.

Writing a composition score function should be easy. The slightly harder part is getting the right weight matrices in the exercises that come after.
```




Let's calculate this metric for all pairs of heads in layer 0 and layer 1 for each of K, Q and V composition and plot it.

We'll start by implementing this using plain old tensors (later on we'll see how this can be sped up using the `FactoredMatrix` class). We also won't worry about batching our calculations yet; we'll just do one matrix at a time.

We've given you tensors `q_comp_scores` etc. to hold the composition scores for each of Q, K and V composition (i.e. the `[i, j]`th element of `q_comp_scores` is the Q-composition score between the output from the `i`th head in layer 0 and the input to the `j`th head in layer 1). You should complete the function `get_comp_score`, and then fill in each of these tensors.


```python
def get_comp_score(
    W_A: Float[Tensor, "in_A out_A"], 
    W_B: Float[Tensor, "out_A out_B"]
) -> float:
    '''
    Return the composition score between W_A and W_B.
    '''
    pass


if MAIN:
    tests.test_get_comp_score(get_comp_score)

```

Once you've passed the tests, you can fill in all the composition scores. Here you should just use a for loop, iterating over all possible pairs of `W_A` in layer 0 and `W_B` in layer 1, for each type of composition. Later on, we'll look at ways to batch this computation.


```python
# Get all QK and OV matrices

if MAIN:
    W_QK = model.W_Q @ model.W_K.transpose(-1, -2)
    W_OV = model.W_V @ model.W_O
    
    # Define tensors to hold the composition scores
    composition_scores = {
        "Q": t.zeros(model.cfg.n_heads, model.cfg.n_heads).to(device),
        "K": t.zeros(model.cfg.n_heads, model.cfg.n_heads).to(device),
        "V": t.zeros(model.cfg.n_heads, model.cfg.n_heads).to(device),
    }
    
    # YOUR CODE HERE - fill in each tensor in the dictionary, by looping over W_A and W_B from layers 0 and 1
    for comp_type in "QKV":
        plot_comp_scores(model, composition_scores[comp_type], f"{comp_type} Composition Scores").show()

```

<details>
<summary>Solution </summary>

```python
def get_comp_score(
    W_A: Float[Tensor, "in_A out_A"], 
    W_B: Float[Tensor, "out_A out_B"]
) -> float:
    '''
    Return the composition score between W_A and W_B.
    '''
    # SOLUTION
    W_A_norm = W_A.pow(2).sum().sqrt()
    W_B_norm = W_B.pow(2).sum().sqrt()
    W_AB_norm = (W_A @ W_B).pow(2).sum().sqrt()

    return (W_AB_norm / (W_A_norm * W_B_norm)).item()


# Get all QK and OV matrices
W_QK = model.W_Q @ model.W_K.transpose(-1, -2)
W_OV = model.W_V @ model.W_O

# Define tensors to hold the composition scores
composition_scores = {
    "Q": t.zeros(model.cfg.n_heads, model.cfg.n_heads).to(device),
    "Κ": t.zeros(model.cfg.n_heads, model.cfg.n_heads).to(device),
    "V": t.zeros(model.cfg.n_heads, model.cfg.n_heads).to(device),
}

# Fill in the tensors, by looping over W_A and W_B from layers 0 and 1
for i in tqdm(range(model.cfg.n_heads)):
    for j in range(model.cfg.n_heads):
        composition_scores["Q"][i, j] = get_comp_score(W_OV[0, i], W_QK[1, j])
        composition_scores["K"][i, j] = get_comp_score(W_OV[0, i], W_QK[1, j].T)
        composition_scores["V"][i, j] = get_comp_score(W_OV[0, i], W_OV[1, j])
```
</details>


### Exercise - Setting a Baseline

```c
Difficulty: 🟠🟠⚪⚪⚪
Importance: 🟠🟠⚪⚪⚪

You shouldn't spend more than ~10 minutes on this exercise.
```

To interpret the above graphs we need a baseline! A good one is what the scores look like at initialisation. Make a function that randomly generates a composition score 200 times and tries this. Remember to generate 4 `[d_head, d_model]` matrices, not 2 `[d_model, d_model]` matrices! This model was initialised with **Kaiming Uniform Initialisation**:

```python
W = t.empty(shape)
nn.init.kaiming_uniform_(W, a=np.sqrt(5))
```

(Ideally we'd do a more efficient generation involving batching, and more samples, but we won't worry about that yet.)


```python
def generate_single_random_comp_score() -> float:
    '''
    Write a function which generates a single composition score for random matrices
    '''
    pass


if MAIN:
    n_samples = 300
    comp_scores_baseline = np.zeros(n_samples)
    for i in tqdm(range(n_samples)):
        comp_scores_baseline[i] = generate_single_random_comp_score()
    print("\nMean:", comp_scores_baseline.mean())
    print("Std:", comp_scores_baseline.std())
    hist(
        comp_scores_baseline, 
        nbins=50, 
        width=800, 
        labels={"x": "Composition score"}, 
        title="Random composition scores"
    )

```

<details>
<summary>Solution</summary>


```python
def generate_single_random_comp_score() -> float:
    '''
    Write a function which generates a single composition score for random matrices
    '''
    # SOLUTION
    W_A_left = t.empty(model.cfg.d_model, model.cfg.d_head)
    W_B_left = t.empty(model.cfg.d_model, model.cfg.d_head)
    W_A_right = t.empty(model.cfg.d_model, model.cfg.d_head)
    W_B_right = t.empty(model.cfg.d_model, model.cfg.d_head)

    for W in [W_A_left, W_B_left, W_A_right, W_B_right]:
        nn.init.kaiming_uniform_(W, a=np.sqrt(5))

    W_A = W_A_left @ W_A_right.T
    W_B = W_B_left @ W_B_right.T

    return get_comp_score(W_A, W_B)
```
</details>


We can re-plot our above graphs with this baseline set to white. Look for interesting things in this graph!


```python

if MAIN:
    baseline = comp_scores_baseline.mean()
    for comp_type, comp_scores in composition_scores.items():
        plot_comp_scores(model, comp_scores, f"{comp_type} Composition Scores", baseline=baseline)

```

<details>
<summary>Some interesting things to observe:</summary>

The most obvious thing that jumps out (when considered in the context of all the analysis we've done so far) is the K-composition scores. `0.7` (the prev token head) is strongly composing with `1.4` and `1.10` (the two attention heads). This is what we expect, and is a good indication that our composition scores are working as intended.

Another interesting thing to note is that the V-composition scores for heads `1.4` and `1.10` with all other heads in layer 0 are very low. In the context of the induction circuit, this is a good thing - the OV circuits of our induction heads should be operating on the **embeddings**, rather than the outputs of the layer-0 heads. (If our repeating sequence is `A B ... A B`, then it's the QK circuit's job to make sure the second `A` attends to the first `B`, and it's the OV circuit's job to project the residual vector at that position onto the **embedding space** in order to extract the `B`-information, while hopefully ignoring anything else that has been written to that position by the heads in layer 0). So once again, this is a good sign for our composition scores.

<img src="https://raw.githubusercontent.com/callummcdougall/computational-thread-art/master/example_images/misc/small_comp_diagram_last.png" width="750">

</details>



#### Theory + Efficient Implementation

So, what's up with that metric? The key is a cute linear algebra result that the squared Frobenius norm is equal to the sum of the squared singular values.

<details>
<summary>Proof</summary>

We'll give three different proofs:

---

##### Short sketch of proof

Clearly $\|M\|_F^2$ equals the sum of squared singular values when $M$ is diagonal. The singular values of $M$ don't change when we multiply it by an orthogonal matrix (only the matrices $U$ and $V$ will change, not $S$), so it remains to show that the Frobenius norm also won't change when we multiply $M$ by an orthogonal matrix. But this follows from the fact that the Frobenius norm is the sum of the squared $l_2$ norms of the column vectors of $M$, and orthogonal matrices preserve $l_2$ norms. (If we're right-multiplying $M$ by an orthogonal matrix, then we instead view this as performing orthogonal operations on the row vectors of $M$, and the same argument holds.)

---

##### Long proof

$$
\begin{aligned}
\|M\|_F^2 &= \sum_{ij}M_{ij}^2 \\
&= \sum_{ij}((USV^T)_{ij})^2 \\
&= \sum_{ij}\bigg(\sum_k U_{ik}S_{kk}V_{jk}\bigg)^2 \\
&= \sum_{ijk_1 k_2}S_{k_1 k_1} S_{k_2 k_2} U_{i k_1} U_{i k_2} V_{j k_2} V_{j k_2} \\
&= \sum_{k_1 k_2}S_{k_1 k_1} S_{k_2 k_2} \bigg(\sum_i U_{i k_1} U_{i k_2}\bigg)\bigg(\sum_j V_{j k_2} V_{j k_2}\bigg) \\
\end{aligned}
$$

Each of the terms in large brackets is actually the dot product of columns of $U$ and $V$ respectively. Since these are orthogonal matrices, these terms evaluate to 1 when $k_1=k_2$ and 0 otherwise. So we are left with:

$$
\|M\|_F^2 = \sum_{k}S_{k k}^2
$$

---

##### Cute proof which uses the fact that the squared Frobenius norm $|M|^2$ is the same as the trace of $MM^T$

$$
\|M\|_F^2 = \text{Tr}(MM^T) = \text{Tr}(USV^TVSU^T) = \text{Tr}(US^2U^T) = \text{Tr}(S^2 U^T U) = \text{Tr}(S^2) = \|S\|_F^2
$$

where we used the cyclicity of trace, and the fact that $U$ is orthogonal so $U^TU=I$ (and same for $V$). We finish by observing that $\|S\|_F^2$ is precisely the sum of the squared singular values.
</details>


So if $W_A=U_AS_AV_A^T$, $W_B=U_BS_BV_B^T$, then $\|W_A\|_F=\|S_A\|_F$, $\|W_B\|_F=\|S_B\|_F$ and $\|W_AW_B\|_F=\|S_AV_A^TU_BS_B\|_F$. In some sense, $V_A^TU_B$ represents how aligned the subspaces written to and read from are, and the $S_A$ and $S_B$ terms weights by the importance of those subspaces.

<details>
<summary>Click here, if this explanation still seems confusing.</summary>

$U_B$ is a matrix of shape `[d_model, d_head]`. It represents **the subspace being read from**, i.e. our later head reads from the residual stream by projecting it onto the `d_head` columns of this matrix.

$V_A$ is a matrix of shape `[d_model, d_head]`. It represents **the subspace being written to**, i.e. the thing written to the residual stream by our earlier head is a linear combination of the `d_head` column-vectors of $V_A$.

$V_A^T U_B$ is a matrix of shape `[d_head, d_head]`. Each element of this matrix is formed by taking the dot product of two vectors of length `d_model`:

* $v_i^A$, a column of $V_A$ (one of the vectors our earlier head embeds into the residual stream)
* $u_j^B$, a column of $U_B$ (one of the vectors our later head projects the residual stream onto)

Let the singular values of $S_A$ be $\sigma_1^A, ..., \sigma_k^A$ and similarly for $S_B$. Then:

$$
\|S_A V_A^T U_B S_B\|_F^2 = \sum_{i,j=1}^k (\sigma_i^A \sigma_j^B)^2 \|v^A_i \cdot u^B_j\|_F^2
$$

This is a weighted sum of the squared cosine similarity of the columns of $V_A$ and $U_B$ (i.e. the output directions of the earlier head and the input directions of the later head). The weights in this sum are given by the singular values of both $S_A$ and $S_B$ - i.e. if $v^A_i$ is an important output direction, **and** $u_B^i$ is an important input direction, then the composition score will be much higher when these two directions are aligned with each other.

---

To build intuition, let's consider a couple of extreme examples.

* If there was no overlap between the spaces being written to and read from, then $V_A^T U_B$ would be a matrix of zeros (since every $v_i^A \cdot u_j^B$ would be zero). This would mean that the composition score would be zero.
* If there was perfect overlap, i.e. the span of the $v_i^A$ vectors and $u_j^B$ vectors is the same, then the composition score is large. It is as large as possible when the most important input directions and most important output directions line up (i.e. when the singular values $\sigma_i^A$ and $\sigma_j^B$ are in the same order).
* If our matrices $W_A$ and $W_B$ were just rank 1 (i.e. $W_A = \sigma_A u_A v_A^T$, and $W_B = \sigma_B u_B v_B^T$), then the composition score is $|v_A^T u_B|$, in other words just the cosine similarity of the single output direction of $W_A$ and the single input direction of $W_B$.
</details>


### Exercise - batching, and using the `FactoredMatrix` class

```c
Difficulty: 🟠🟠🟠🟠⚪
Importance: 🟠⚪⚪⚪⚪

This exercise is optional, and not a vitally important conceptual part  of this section. It's also quite messy to rearrange our tensors in the right way! You are invited to skip it if you want.
```


We can also use this insight to write a more efficient way to calculate composition scores - this is extremely useful if you want to do this analysis at scale! The key is that we know that our matrices have a low rank factorisation, and it's much cheaper to calculate the SVD of a narrow matrix than one that's large in both dimensions. See the [algorithm described at the end of the paper](https://transformer-circuits.pub/2021/framework/index.html#induction-heads:~:text=Working%20with%20Low%2DRank%20Matrices) (search for SVD).

So we can work with the `FactoredMatrix` class. This also provides the method `.norm()` which returns the Frobenium norm. This is also a good opportunity to bring back baching - this will sometimes be useful in our analysis. In the function below, `W_As` and `W_Bs` are both >2D factored matrices (e.g. they might represent the OV circuits for all heads in a particular layer, or across multiple layers), and the function's output should be a tensor of composition scores for each pair of matrices `(W_A, W_B)` in the >2D tensors `(W_As, W_Bs)`.


```python
def get_batched_comp_scores(
    W_As: FactoredMatrix,
    W_Bs: FactoredMatrix
) -> t.Tensor:
    '''Computes the compositional scores from indexed factored matrices W_As and W_Bs.

    Each of W_As and W_Bs is a FactoredMatrix object which is indexed by all but its last 2 dimensions, i.e.:
        W_As.shape == (*A_idx, A_in, A_out)
        W_Bs.shape == (*B_idx, B_in, B_out)
        A_out == B_in

    Return: tensor of shape (*A_idx, *B_idx) where the [*a_idx, *b_idx]th element is the compositional score from W_As[*a_idx] to W_Bs[*b_idx].
    '''
    pass


if MAIN:
    W_QK = FactoredMatrix(model.W_Q, model.W_K.transpose(-1, -2))
    W_OV = FactoredMatrix(model.W_V, model.W_O)
    
    composition_scores_batched = dict()
    composition_scores_batched["Q"] = get_batched_comp_scores(W_OV[0], W_QK[1])
    composition_scores_batched["K"] = get_batched_comp_scores(W_OV[0], W_QK[1].T) # Factored matrix: .T is interpreted as transpose of the last two axes
    composition_scores_batched["V"] = get_batched_comp_scores(W_OV[0], W_OV[1])
    
    t.testing.assert_close(composition_scores_batched["Q"], composition_scores["Q"])
    t.testing.assert_close(composition_scores_batched["K"], composition_scores["K"])
    t.testing.assert_close(composition_scores_batched["V"], composition_scores["V"])
    print("Tests passed - your `get_batched_comp_scores` function is working!")

```

<details>
<summary>Hint</summary>

Suppose `W_As` has shape `(A1, A2, ..., Am, A_in, A_out)` and `W_Bs` has shape `(B1, B2, ..., Bn, B_in, B_out)` (where `A_out == B_in`).

It will be helpful to reshape these two tensors so that:

```python
W_As.shape == (A1*A2*...*Am, 1, A_in, A_out)
W_Bs.shape == (1, B1*B2*...*Bn, B_in, B_out)
```

since we can then multiply them together as `W_As @ W_Bs` (broadcasting will take care of this for us!).

To do the reshaping, the easiest way is to reshape `W_As.A` and `W_As.B`, and define a new `FactoredMatrix` from these reshaped tensors (and same for `W_Bs`).
</details>

<details>
<summary>Solution</summary>


```python
def get_batched_comp_scores(
    W_As: FactoredMatrix,
    W_Bs: FactoredMatrix
) -> t.Tensor:
    '''Computes the compositional scores from indexed factored matrices W_As and W_Bs.

    Each of W_As and W_Bs is a FactoredMatrix object which is indexed by all but its last 2 dimensions, i.e.:
        W_As.shape == (*A_idx, A_in, A_out)
        W_Bs.shape == (*B_idx, B_in, B_out)
        A_out == B_in

    Return: tensor of shape (*A_idx, *B_idx) where the [*a_idx, *b_idx]th element is the compositional score from W_As[*a_idx] to W_Bs[*b_idx].
    '''
    # SOLUTION
    W_As = FactoredMatrix(
        W_As.A.reshape(-1, 1, *W_As.A.shape[-2:]),
        W_As.B.reshape(-1, 1, *W_As.B.shape[-2:]),
    )
    W_Bs = FactoredMatrix(
        W_Bs.A.reshape(1, -1, *W_Bs.A.shape[-2:]),
        W_Bs.B.reshape(1, -1, *W_Bs.B.shape[-2:]),
    )

    # Compute the product
    W_ABs = W_As @ W_Bs

    # Compute the norms, and return the metric
    return W_ABs.norm() / (W_As.norm() * W_Bs.norm())
```
</details>


### Targeted Ablations

We can refine the ablation technique to detect composition by looking at the effect of the ablation on the attention pattern of an induction head, rather than the loss. Let's implement this!

Gotcha - by default, `run_with_hooks` removes any existing hooks when it runs. If you want to use caching, set the `reset_hooks_start` flag to False.


```python
def ablation_induction_score(prev_head_index: Optional[int], ind_head_index: int) -> float:
    '''
    Takes as input the index of the L0 head and the index of the L1 head, and then runs with the previous token head ablated and returns the induction score for the ind_head_index now.
    '''

    def ablation_hook(v, hook):
        if prev_head_index is not None:
            v[:, :, prev_head_index] = 0.0
        return v

    def induction_pattern_hook(attn, hook):
        hook.ctx[prev_head_index] = attn[0, ind_head_index].diag(-(seq_len - 1)).mean()

    model.run_with_hooks(
        rep_tokens,
        fwd_hooks=[
            (utils.get_act_name("v", 0), ablation_hook),
            (utils.get_act_name("pattern", 1), induction_pattern_hook)
        ],
    )
    return model.blocks[1].attn.hook_pattern.ctx[prev_head_index].item()



if MAIN:
    baseline_induction_score = ablation_induction_score(None, 4)
    print(f"Induction score for no ablations: {baseline_induction_score:.5f}\n")
    for i in range(model.cfg.n_heads):
        new_induction_score = ablation_induction_score(i, 4)
        induction_score_change = new_induction_score - baseline_induction_score
        print(f"Ablation score change for head {i:02}: {induction_score_change:+.5f}")

```

<details>
<summary>Question - what is the interpretation of the results you're getting?</summary>

You should have found that the induction score without any ablations is about 0.68, and that most other heads don't change the induction score by much when they are ablated, except for head 7 which reduces the induction score to nearly zero.

This is another strong piece of evidence that head `0.7` is the prev token head in this induction circuit.
</details>


## Bonus

### Looking for Circuits in Real LLMs

A particularly cool application of these techniques is looking for real examples of circuits in large language models. Fortunately, there's a bunch of open source ones you can play around with in the `TransformerLens` library! Many of the techniques we've been using for our 2L transformer carry over to ones with more layers.

This library should make it moderately easy to play around with these models - I recommend going wild and looking for interesting circuits!

Some fun things you might want to try:

- Look for induction heads - try repeating all of the steps from above. Do they follow the same algorithm?
- Look for neurons that erase info
    - i.e. having a high negative cosine similarity between the input and output weights
- Try to interpret a position embedding.

<details>
<summary>Positional Embedding Hint</summary>

Look at the singular value decomposition `t.svd` and plot the principal components over position space. High ones tend to be sine and cosine waves of different frequencies.
</details>

- Look for heads with interpretable attention patterns: e.g. heads that attend to the same word (or subsequent word) when given text in different languages, or the most recent proper noun, or the most recent full-stop, or the subject of the sentence, etc.
    - Pick a head, ablate it, and run the model on a load of text with and without the head. Look for tokens with the largest difference in loss, and try to interpret what the head is doing.
- Try replicating some of Kevin's work on indirect object identification.
- Inspired by the [ROME paper](https://rome.baulab.info/), use the causal tracing technique of patching in the residual stream - can you analyse how the network answers different facts?

Note: I apply several simplifications to the resulting transformer - these leave the model mathematically equivalent and doesn't change the output log probs, but does somewhat change the structure of the model and one change translates the output logits by a constant.

<details>
<summary>Model simplifications</summary>

#### Centering $W_U$

The output of $W_U$ is a $d_{vocab}$ vector (or tensor with that as the final dimension) which is fed into a softmax

#### LayerNorm Folding

LayerNorm is only applied at the start of a linear layer reading from the residual stream (eg query, key, value, mlp_in or unembed calculations)

Each LayerNorm has the functional form $LN:\mathbb{R}^n\to\mathbb{R}^n$, 
$LN(x)=s(x) * w_{ln} + b_{ln}$, where $*$ is element-wise multiply and $s(x)=\frac{x-\bar{x}}{|x-\bar{x}|}$, and $w_{ln},b_{ln}$ are both vectors in $\mathbb{R}^n$

The linear layer has form $l:\mathbb{R}^n\to\mathbb{R}^m$, $l(y)=Wy+b$ where $W\in \mathbb{R}^{m\times n},b\in \mathbb{R}^m,y\in\mathbb{R}^n$

So $f(LN(x))=W(w_{ln} * s(x)+b_{ln})+b=(W * w_{ln})s(x)+(Wb_{ln}+b)=W_{eff}s(x)+b_{eff}$, where $W_{eff}$ is the elementwise product of $W$ and $w_{ln}$ (showing that elementwise multiplication commutes like this is left as an exercise) and $b_{eff}=Wb_{ln}+b\in \mathbb{R}^m$.

From the perspective of interpretability, it's much nicer to interpret the folded layer $W_{eff},b_{eff}$ - fundamentally, this is the computation being done, and there's no reason to expect $W$ or $w_{ln}$ to be meaningful on their own. 
</details>


### Training Your Own Toy Models

A fun exercise is training models on the minimal task that'll produce induction heads - predicting the next token in a sequence of random tokens with repeated subsequences. You can get a small 2L Attention-Only model to do this.

<details>
<summary>Tips</summary>

* Make sure to randomise the positions that are repeated! Otherwise the model can just learn the boring algorithm of attending to fixed positions
* It works better if you *only* evaluate loss on the repeated tokens, this makes the task less noisy.
* It works best with several repeats of the same sequence rather than just one.
* If you do things right, and give it finite data + weight decay, you *should* be able to get it to grok - this may take some hyper-parameter tuning though.
* When I've done this I get weird franken-induction heads, where each head has 1/3 of an induction stripe, and together cover all tokens.
* It'll work better if you only let the queries and keys access the positional embeddings, but *should* work either way.
</details>


### Interpreting Induction Heads During Training

A particularly striking result about induction heads is that they consistently [form very abruptly in training as a phase change](https://transformer-circuits.pub/2022/in-context-learning-and-induction-heads/index.html#argument-phase-change), and are such an important capability that there is a [visible non-convex bump in the loss curve](https://wandb.ai/mechanistic-interpretability/attn-only/reports/loss_ewma-22-08-24-22-08-00---VmlldzoyNTI2MDM0?accessToken=r6v951q0e1l4q4o70wb2q67wopdyo3v69kz54siuw7lwb4jz6u732vo56h6dr7c2) (in this model, approx 2B to 4B tokens). I have a bunch of checkpoints for this model, you can try re-running the induction head detection techniques on intermediate checkpoints and see what happens. (Bonus points if you have good ideas for how to efficiently send a bunch of 300MB checkpoints from Wandb lol)


### Further discussion / investigation

Anthropic has written a post on [In-context Learning and Induction Heads](https://transformer-circuits.pub/2022/in-context-learning-and-induction-heads/index.html) which goes into much deeper discussion on induction heads. The post is structured around six different points of evidence for the hypothesis that **induction heads are the main source of in-context learning in transformer models**, even large ones. Briefly, these are:

1. Transformers undergo a "phase change" where they suddenly become much better at in-context learning, and this is around the same time induction heads appear.
2. When we change the transformer's architecture to make it easier for induction heads to form, we get a corresponding improvement in in-context learning.
3. When we ablate induction heads at runtime, in-context learning gets worse.
4. We have specific examples of induction heads performing more complex in-context learning algorithms (you'll have the opportunity to investigate one of these later - **indirect object identification**).
5. We have a mechanistic explanation of induction heads, which suggests natural extensions to more general forms of in-context learning.
6. In-context learning-related behaviour is generally smoothly continuous between small and large models, suggesting that the underlying mechanism is also the same.

Here are a few questions for you:

* How compelling do you find this evidence? Discuss with your partner.
    * Which points do you find most compelling? 
    * Which do you find least compelling?
    * Are there any subset of these which would be enough to convince you of the hypothesis, in the absence of others?
* In point 3, the paper observes that in-context learning performance degrades when you ablate induction heads. While we measured this by testing the model's ability to copy a duplicated random sequence, the paper used **in-context learning score** (the loss of the 500th token in the context, minus the loss on the 50th token).
    * Can you see why this is a reasonable metric? 
    * Can you replicate these results (maybe on a larger model than the 2-layer one we've been using)?
* In point 4 (more complex forms of in-context learning), the paper suggests the natural extension of "fuzzy induction heads", which match patterns like `[A*][B*]...[A][B]` rather than `[A][B]...[A][B]` (where the `*` indicates some form of linguistic similarity, not necessarily being the same token).
    * Can you think of any forms this might take, i.e. any kinds of similarity which induction heads might pick up on? Can you generate examples?





""", unsafe_allow_html=True)


func_page_list = [
    (section_0, "🏠 Home"),     (section_1, "1️⃣ TransformerLens: Introduction"),     (section_2, "2️⃣ Finding induction heads"),     (section_3, "3️⃣ TransformerLens: Hooks"),     (section_4, "4️⃣ Reverse-engineering induction circuits"), 
]

func_list = [func for func, page in func_page_list]
page_list = [page for func, page in func_page_list]

page_dict = dict(zip(page_list, range(len(page_list))))

def page():
    with st.sidebar:
        radio = st.radio("Section", page_list)
        st.markdown("---")
    idx = page_dict[radio]
    func = func_list[idx]
    func()

page()
