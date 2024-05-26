start-minio:
	sudo systemctl start minio.service 

start-server:
	python -m streamlit run app/web/Home.py