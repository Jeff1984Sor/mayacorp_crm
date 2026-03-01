from app.services.bootstrap import bootstrap_central_database


if __name__ == "__main__":
    bootstrap_central_database()
    print("Central database bootstrapped.")
