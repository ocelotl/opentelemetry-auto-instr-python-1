import os

if __name__ == '__main__':
    assert os.environ['OPENTELEMETRY_SERVICE_NAME'] == 'my_test_service'
    print('Test success')
