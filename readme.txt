# some efforts to digitize turing archive 

the archivist at kings college told me that there are so many things turing wrote which are not digitized and they are massively understaffed and underfunded. so i will just try to write some llm shit together to parse turing works and create a pdf compendium. 

will host it on my website in a nice viewer too. 

[] start with a turing pdf 
[] extract fig 
[] extract ocr 
[] ensure fig is in a correct place 
[] ensure latex code works and compiles 
[] ensure a combined pipeline is ready. 
[] beautify whole thing in a single folder.
[] expose as a shitty api lol
use open source llm , cant afford to pay gemini lol. 
needs some vlm mebbe . 

uggh -> deepseek, qwen?
will see..




# run vllm server 

# some resources that i need. 

https://www.alanturing.net/index.htm


just logging what i did 

1. read pdf -> first pass thru gemini 2.5 flash lite at 150dpi of pdf 
            -> combines latex code -> second pass thru gemini 2.5 pro to get consistent latex 
            -> dump latex 
            -> use xelatex to compile lol. 
