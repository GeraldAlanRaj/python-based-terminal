# Flask-based web UI for the terminal
from flask import Flask, request, render_template, jsonify
from core.terminal import Terminal
from core.ai import interpret_natural_language

app = Flask(__name__)
terminal = Terminal()

@app.route('/', methods=['GET', 'POST'])
def index():
    output = ""
    if request.method == 'POST':
        cmd = request.form.get('command', '')
        # AI interpretation
        if cmd and not cmd.split()[0] in terminal.builtins:
            ai_cmd = interpret_natural_language(cmd)
            if ai_cmd:
                cmd = ai_cmd
        output = terminal.execute_line(cmd)
    return render_template('index.html', output=output)

if __name__ == '__main__':
    app.run(debug=True)
