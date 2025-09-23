: 1758534549:0;uv init --python 3.12
: 1758534570:0;uv .venv --pyhton 3.12
: 1758534580:0;uv venv --pyhton 3.12
: 1758534588:0;uv venv --python 3.12
: 1758534596:0;source .venv/bin/activate\

: 1758543133:0;uv add -r requirements.txt
: 1758591718:0;source .venv/bin/activate
: 1758591768:0;uv add nbformat>4.2.0
: 1758593416:0;uv add scipy
: 1758597257:0;tree
: 1758608478:0;uv add matplotlib
: 1758616390:0;source /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/activate
: 1758616398:0;claude
: 1758617474:0;mv *png figure
: 1758617702:0;mv *.png Q1/figure
: 1758621595:0;/home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/python /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/data_process/json_descriptive_statistics.py
: 1758628640:0;find Attachment/Problem3 -name "*.txt" | sort
: 1758630444:0;ls -la Attachment/Problem3/ | wc -l
: 1758630452:0;ls -la Attachment/Problem3/ | tail -5
: 1758633143:0;ssh furong
: 1758633303:0;scp /home/lanshi/Desktop/Q3.zip furong:~
: 1758633518:0;# æƒ¶¹æ³ƒµ1: ä½¿çƒ´¨jupyter nbconvert\
jupyter nbconvert --to script Q_3.ipynb --output Q3_optimization\
\
# æƒ¶¹æ³ƒµ2: æƒ©ƒ«åƒª¨åƒ¨ƒ»å»ºPythonèƒ¤ƒºæƒ¼¬\
# filepath: /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/Q3_optimization.py
: 1758633675:0;scp /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/Q_3.py furong:~/Q3/
: 1758635745:0;ssh furong
: 1758638220:0;cd ~/Downloads
: 1758638237:0;scp uv-x86_64-unknown-linux-gnu.tar.gz furong ~/bin
: 1758638245:0;scp uv-x86_64-unknown-linux-gnu.tar.gz furong:~/bin
: 1758638387:0;ls
: 1758638704:0;ssh furong
: 1758638774:0;scp uv-installer.sh furong:~/bin/uv
: 1758680916:0;python Q_3_view.py --mode comparison --open
: 1758680930:0;source .venv/bin/activate
: 1758680932:0;python Q_3_view.py --mode comparison --open
: 1758681551:0;source /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/activate
: 1758694807:0;claude
: 1758701612:0;source /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/activate
: 1758701612:0;/home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/python /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/Q3/code/Q_3_new.py
: 1758701653:0;/home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/python /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/Q3/code/Q_3_optimized.py
: 1758702929:0;claude
: 1758705578:0;source /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/activate
: 1758705578:0;/home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/python /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/Q2/code/Q_2.py
: 1758706930:0;/home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/python /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/Q2/code/Q_2_view.py
: 1758707037:0;/home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/python /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/Q_2_view.py
: 1758708580:0;claude
: 1758723604:0;/home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/python /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/Q2/code/Q_2_view.py
: 1758723615:0;/home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/python /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/Q_2_view.py
: 1758723816:0;/home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/.venv/bin/python /home/lanshi/Documents/Projects/mathmodels-projects/2025-CPGMCM/code/Q2/code/Q_2_view.py
