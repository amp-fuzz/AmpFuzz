all: eval/Makefile

eval/Makefile: eval/package_matches.json eval/gen_makefile.py
	cd eval && python3 gen_makefile.py > Makefile

eval/package_matches.json: ../03_join_matches/package_matches.json
	cp ../03_join_matches/package_matches.json eval/

.PHONY: clean

clean:
	rm -rf eval/Makefile eval/package_matches.json eval/failed_instrumentation.txt eval/success_instrumentation.txt eval/failed_packages.txt
