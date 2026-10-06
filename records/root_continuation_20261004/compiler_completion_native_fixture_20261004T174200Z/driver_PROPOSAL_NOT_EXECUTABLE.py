"""NONEXECUTING interface placeholder. Adapter API and ROOT admission are pending."""
import json

def main():
    # Intentionally no adapter/supervisor import, worker launch or Windows API.
    print(json.dumps({'status':'NOT_CHECKED','reason':'Pending actual adapter API/source pins, pure QA and separate ROOT native admission','scope':'SOURCE_ONLY_DRIVER_PROPOSAL_NOT_A_NATIVE_RUN'}))
    return 2

if __name__ == '__main__':
    raise SystemExit(main())
