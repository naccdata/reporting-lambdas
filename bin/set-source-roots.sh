#!/bin/sh
ROOTS=$(pants roots)
python3 -c "print('PYTHONPATH=\"./' + ':./'.join('''${ROOTS}'''.split('\n')) + ':\$PYTHONPATH\"')" > .env
